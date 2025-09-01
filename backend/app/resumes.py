import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from .s3_client import s3, BUCKET

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
