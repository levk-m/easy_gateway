from fastapi import APIRouter, Depends, HTTPException, Request
from loguru import logger

from easy_gateway.gateway.admin.security import auth_user
from easy_gateway.router.router import RouteType

router = APIRouter(
    prefix="/admin", tags=["Gateway Admin Panel"], dependencies=[Depends(auth_user)]
)
PREFIX: str = "[ADMIN]"


@router.post("/add_route")
def add_route(req: Request, path: str, target: str) -> dict[str, str]:
    gateway = req.app.state.gateway
    gateway.router.validate(path, target)
    gateway.router.add_route(path, target)

    logger.info(f"{PREFIX} ✅ Route added: {path} --> {target}")

    return {"status": "success", "path": path, "target": target}


@router.delete("/del_route")
def delete_route(req: Request, path: str) -> dict[str, str]:
    gateway = req.app.state.gateway
    if gateway.router.delete_route(path):
        logger.info(f"{PREFIX} ✅ route {path} deleted!")
        return {"status": "success", "message": f"Route '{path}' deleted"}

    logger.error(f"{PREFIX} ❌ route {path} not found")
    return {"status": "error", "message": f"Route '{path}' not found"}


@router.get("/all_routes")
def show_all_routes(req: Request) -> dict[str, dict[str, dict[str, str]] | str]:
    gateway = req.app.state.gateway
    exact = gateway.router.exact_routes
    prefix = gateway.router.prefix_routes

    def format_routes(routes):
        if not routes:
            return "It's empty :("
        return {path: {"url": data[0]} for path, data in routes.items()}

    return {
        "Exact routes": format_routes(exact),
        "Prefix routes": format_routes(prefix),
    }


@router.put("/update/{path:path}")
def update_route(req: Request, path: str, new_target: str) -> dict[str, str]:
    gateway = req.app.state.gateway
    try:
        gateway.router.update_route(path, new_target)
        logger.info(f"[ADMIN] ✅ Route updated: {path} -> {new_target}")
        return {"status": "success", "path": path, "target": new_target}
    except Exception as e:
        logger.error(f"[ADMIN] ❌ Failed to update route {path}: {e}")
        raise HTTPException(500, f"Failed to update route: {str(e)}")


@router.get("/check/{path:path}")
def find_path(req: Request, path: str) -> dict[str, str | RouteType | None] | str:
    gateway = req.app.state.gateway
    result = gateway.router.find_target(path)

    if result[0] is None:
        return f"🧐 Path {path} not found"

    target, remaining, route_type = result
    return {"target": target, "remaining": remaining, "route_type": route_type}
