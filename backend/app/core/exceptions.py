
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class SmartCampusException(HTTPException):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(
            status_code=status_code,
            detail=message
        )


async def smartcampus_exception_handler(
    request: Request,
    exc: SmartCampusException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )
