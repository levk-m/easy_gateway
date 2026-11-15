from enum import Enum
from urllib.parse import urljoin

from fastapi import HTTPException
from loguru import logger


class RouteType(Enum):
    EXACT = "exact"
    PREFIX = "prefix"


class Router:
    def __init__(self) -> None:
        self.exact_routes: dict[str, tuple[str, RouteType]] = {}
        self.prefix_routes: dict[str, tuple[str, RouteType]] = {}

    def validate(self, path: str, target: str):
        if not (target.startswith("http://") or target.startswith("https://")):
            detail = "Target must be a full URL (with http:// or https://)"
            logger.error(f"[ADMIN] Bad Request: {detail}")
            raise HTTPException(status_code=400, detail=detail)

    def add_route(self, path: str, target: str):
        self.validate(path, target)
        if path.endswith("/*"):
            prefix = path[:-2]
            self.prefix_routes[prefix] = (target.rstrip("/"), RouteType.PREFIX)
        else:
            full_url = urljoin(target.rstrip("/") + "/", path.lstrip("/"))
            self.exact_routes[path] = (full_url, RouteType.EXACT)

    def delete_route(self, path: str) -> bool:
        deleted = False
        if path in self.prefix_routes:
            del self.prefix_routes[path]
            deleted = True
        if path in self.exact_routes:
            del self.exact_routes[path]
            deleted = True
        return deleted

    def find_target(
        self, request_path: str
    ) -> tuple[str | None, str, RouteType | None]:
        if request_path in self.exact_routes:
            target, route_type = self.exact_routes[request_path]
            return target, "", route_type

        longest_prefix = ""
        best_target = None
        best_route_type = None

        for prefix, (target, route_type) in self.prefix_routes.items():
            if request_path.startswith(prefix):
                if len(prefix) > len(longest_prefix):
                    longest_prefix = prefix
                    best_target = target
                    best_route_type = route_type

        if best_target:
            remaining = request_path[len(longest_prefix) :]
            return best_target, remaining, best_route_type

        return None, "", None

    def update_route(self, path: str, new_target: str) -> bool:
        self.validate(path, new_target)

        if path.endswith("/*"):
            prefix = path[:-2]
            if prefix in self.prefix_routes:
                self.prefix_routes[prefix] = (new_target.rstrip("/"), RouteType.PREFIX)
                return True
            raise HTTPException(404, f"Prefix route '{path}' not found")

        if path in self.exact_routes:
            full_url = urljoin(new_target.rstrip("/") + "/", path.lstrip("/"))
            self.exact_routes[path] = (full_url, RouteType.EXACT)
            return True

        if path in self.prefix_routes:
            self.prefix_routes[path] = (new_target.rstrip("/"), RouteType.PREFIX)
            return True

        raise HTTPException(404, f"Route '{path}' not found")
