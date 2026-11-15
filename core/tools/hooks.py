from collections.abc import Callable

from core.tools.results import ToolResult

type ToolHandler = Callable[..., ToolResult]
type PreHook[S] = Callable[[dict, S], None]  # raise ToolError to block the call
type PostHook[S] = Callable[[ToolResult, S], None]  # observe the result, update the session
