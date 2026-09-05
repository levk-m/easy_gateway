import secrets

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

security = HTTPBasic()


def auth_user(req: Request, credentials: HTTPBasicCredentials = Depends(security)):
    config = req.app.state.gateway.config
    admin_conf = config.get("admin", {})
    admin_pass = admin_conf.get("username", "admin")
    admin_name = admin_conf.get("password", "admin")

    if admin_pass == "admin" or admin_name == "admin":
        logger.warning("⚠ Change username, password for production instead of admin!")

    correct_username = secrets.compare_digest(credentials.username, admin_pass)
    correct_password = secrets.compare_digest(credentials.password, admin_name)

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
