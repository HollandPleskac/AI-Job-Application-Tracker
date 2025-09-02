'use client';

import { useEffect, useState } from 'react';

const API = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

type Resume = {
  id: string;
  filename: string;
  key: string;
  size: number;
  content_type: string;
  status: 'processing' | 'ready' | 'failed';
  created_at: number;
};

export default function ResumesPage() {
  const [items, setItems] = useState<Resume[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<string>('');

  async function fetchResumes() {
    const res = await fetch(`${API}/resumes`, { cache: 'no-store' });
    setItems(await res.json());
  }

  useEffect(() => { fetchResumes(); }, []);

  async function handleUpload() {
    if (!file) return;

    // get presigned post to add to add a resume
    setStage('asking api for upload url...');
    const presignedPost = await fetch(`${API}/resumes/upload-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        filename: file.name,
        content_type: file.type || 'application/octet-stream',
        size: file.size,
      }),
    }).then(r => {
      if (!r.ok) throw new Error('upload-url failed');
      return r.json();
    });

    // use it to send file to s3
    setStage('uploading to s3 ...');
    const form = new FormData();
    Object.entries(presignedPost.fields).forEach(([k, v]) => form.append(k, String(v)));
    if (!('key' in presignedPost.fields)) form.append('key', presignedPost.key); 
    form.append('file', file);
    const s3response = await fetch(presignedPost.url, { method: 'POST', body: form });
    if (!(s3response.status === 201 || s3response.status === 204)) {
      setStage('s3 upload failed');
      return;
    }

    // confirm the upload was successful
    setStage('confirming with api...');
    await fetch(`${API}/resumes/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: presignedPost.key }),
    }).then(r => {
      if (!r.ok) throw new Error('confirm failed');
    });

    setStage('refreshing');
    setFile(null);
    await fetchResumes();
    setStage('done');
    setTimeout(() => setStage(''), 1200);
  }

  async function download(resumeId: string) {
    const r = await fetch(`${API}/resumes/${resumeId}/download-url`);
    const { url } = await r.json();
    window.open(url, '_blank');
  }

  return (
    <main className="mx-auto max-w-2xl p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Resumes</h1>

      <section className="border rounded-2xl p-4 space-y-3">
        <input
          type="file"
          accept=".pdf,.docx,.png,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/png,image/jpeg"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
        <button
          onClick={handleUpload}
          disabled={!file}
          className="bg-black text-white rounded px-3 py-2 disabled:opacity-50"
        >
          Upload
        </button>
        <div className="text-sm text-gray-600">{stage}</div>
      </section>

      <section className="space-y-2">
        {items.length === 0 && <div className="text-gray-600">No resumes yet.</div>}
        <ul className="space-y-2">
          {items.map((r) => (
            <li key={r.id} className="border rounded-xl p-3">
              <div className="font-medium">{r.filename}</div>
              <div className="text-sm text-gray-600">
                {Math.round(r.size / 1024)} KB · {r.status}
              </div>
              <div className="mt-2">
                <button onClick={() => download(r.id)} className="text-sm underline">
                  Download
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
