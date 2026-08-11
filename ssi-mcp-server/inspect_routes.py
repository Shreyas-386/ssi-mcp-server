from app.server import create_server
from starlette.routing import Mount, Route
mcp, _ = create_server()
app = mcp.streamable_http_app()

def print_routes(routes, prefix=""):
    for route in routes:
        if isinstance(route, Mount):
            print(f"Mount: {prefix}{route.path}")
            print_routes(route.routes, prefix + route.path)
        elif isinstance(route, Route):
            print(f"Route: {prefix}{route.path} {route.methods}")
        else:
            print(f"Unknown route type: {prefix}{route.path}")

print_routes(app.routes)
