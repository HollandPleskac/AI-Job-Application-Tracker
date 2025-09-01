import uuid
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field
from .s3_client import s3, BUCKET
import time
from typing import Literal

router = APIRouter(prefix="/resumes", tags=["resumes"])

# pdf, word docs, or images
ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}
MAX_BYTES = 10 * 1024 * 1024  # 10 mega bytes

class UploadURLRequest(BaseModel):
    filename: str
    content_type: str
    size: int = Field(..., ge=1, le=MAX_BYTES)

@router.post("/upload-url")
def get_upload_url(body: UploadURLRequest):
    if body.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, f"Unsupported type {body.content_type}")

    ext = body.filename.split(".")[-1].lower()
    key = f"dev/resumes/{uuid.uuid4()}.{ext}"

    fields = {"Content-Type": body.content_type, "success_action_status": "201"}
    conditions = [
        {"bucket": BUCKET},
        ["content-length-range", 1, MAX_BYTES],
        ["starts-with", "$Content-Type", body.content_type.split("/")[0]],
    ]

    presigned = s3().generate_presigned_post(
        Bucket=BUCKET, Key=key, Fields=fields, Conditions=conditions, ExpiresIn=300
    )
    return {"key": key, **presigned}


# s3 feeature notes

# presigned post (will give info needed to make http post to s3)
# basically lets website directly talk to s3
# official: where the server signs a policy that lets browser do an HTML form POST directly to S3 (can use a key and constraints)
# in this case an http post route i can use to upload a resume to s3



_RESUMES: dict[str, dict] = {}

class ConfirmUpload(BaseModel):
    key: str

class ResumeRow(BaseModel):
    id: str
    filename: str
    key: str
    size: int
    content_type: str
    status: Literal["processing", "ready", "failed"]
    created_at: float

@router.post("/confirm", response_model=ResumeRow)
def confirm_upload(req: ConfirmUpload):
    # make sure the object is actually in S3
    try:
        head = s3().head_object(Bucket=BUCKET, Key=req.key)
    except Exception:
        raise HTTPException(400, "Object not in s3")

    resume_id = str(uuid.uuid4())
    row = {
        "id": resume_id,
        "filename": req.key.split("/")[-1],
        "key": req.key,
        "size": head["ContentLength"],        
        "content_type": head.get("ContentType", "application/octet-stream"),
        "status": "ready", # will do backend processing on resumes for now everything is ready
        "created_at": time.time(),
    }
    _RESUMES[resume_id] = row
    return row

# list resumes (newest first)
@router.get("", response_model=list[ResumeRow])
def list_resumes():
    return sorted(_RESUMES.values(), key=lambda x: x["created_at"], reverse=True)


# short lived download url for a resume (requires resume_id)
@router.get("/{resume_id}/download-url")
def get_download_url(resume_id: str = Path(...)):
    row = _RESUMES.get(resume_id)
    if not row:
        raise HTTPException(404, "resume not found")
    url = s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": BUCKET, "Key": row["key"]},
        ExpiresIn=300,  # 5 minutes
    )
    return {"url": url}