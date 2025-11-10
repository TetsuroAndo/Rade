"""FastAPI application for GitHub webhook receiver."""
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException
from fastapi.responses import JSONResponse
from app.services.webhook_service import WebhookService
from app.core.security import verify_github_signature
from app.core.config import settings
from app.core.logging_config import setup_logging, get_logger
from app.core.exceptions import SecurityError

# Configure logging
setup_logging(level="INFO")
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Rade",
    description="GitHub Webhook to Devin API integration",
    version="0.1.0",
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "rade"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/github/webhook")
async def handle_github_webhook(
    request: Request, background_tasks: BackgroundTasks
) -> JSONResponse:
    """
    Handle GitHub webhook events.

    This endpoint receives webhook events from GitHub, verifies the signature,
    and processes them asynchronously.
    """
    # 1. Get raw body for signature verification
    body = await request.body()

    # 2. Verify GitHub signature
    signature = request.headers.get("X-Hub-Signature-256")
    try:
        if not verify_github_signature(body, signature, settings.github_webhook_secret):
            logger.warning("Invalid webhook signature")
            raise SecurityError("Invalid webhook signature")
    except SecurityError:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 3. Parse JSON payload
    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Error parsing webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 4. Get event type for logging
    event_type = request.headers.get("X-GitHub-Event", "unknown")
    logger.info(f"Received GitHub webhook event: {event_type}")

    # 5. Process webhook asynchronously
    webhook_service = WebhookService()

    async def process_with_error_handling(payload: dict):
        """Process webhook with proper error handling."""
        try:
            await webhook_service.process_webhook(payload)
        except Exception as e:
            logger.error(
                f"Error processing webhook: {e}",
                exc_info=True,
                extra={"event_type": event_type},
            )

    background_tasks.add_task(process_with_error_handling, payload)

    # 6. Return immediate response to avoid GitHub timeout
    return JSONResponse(
        status_code=202,
        content={"status": "accepted", "event": event_type},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
