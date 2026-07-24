from fastapi import HTTPException, status


class ClassFlowError(HTTPException):
    def __init__(
        self,
        detail: str,
        error_code: str = "CLASSFLOW_ERROR",
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> None:
        super().__init__(
            status_code=status_code,
            detail={
                "detail": detail,
                "error_code": error_code,
            },
        )