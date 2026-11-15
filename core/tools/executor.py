from collections.abc import Callable
from functools import partial

from core.agent_logger import logger
from core.tools.errors import INTERNAL, TRANSIENT, VALIDATION, ToolError
from core.tools.hooks import PostHook, PreHook, ToolHandler
from core.tools.results import ToolResult
from core.tools.retry import DEFAULT_RETRY_POLICY, RetryPolicy, run_with_policy
from core.tools.session import ToolSession


class ToolExecutor[S: ToolSession, C]:
    def __init__(
        self,
        handlers: dict[str, ToolHandler],
        retry_policies: dict[str, RetryPolicy] | None = None,
        pre_hooks: dict[str, list[PreHook[S]]] | None = None,
        post_hooks: dict[str, list[PostHook[S]]] | None = None,
        *,
        context_factory: Callable[[S], C],
    ):
        self.handlers = handlers
        self.retry_policies = retry_policies or {}
        self.pre_hooks = pre_hooks or {}
        self.post_hooks = post_hooks or {}
        self.context_factory = context_factory

    def execute(self, tool_name: str, tool_input: dict, session: S) -> ToolResult:
        handler = self.handlers.get(tool_name)
        if not handler:
            return {
                "is_error": True,
                "error_category": VALIDATION,
                "is_retryable": False,
                "content": {"is_tool_found": False, "message": f"Unknown tool: {tool_name}"},
            }

        # PRE HOOKS
        if blocked := self._run_pre_hooks(tool_name, tool_input, session):
            return blocked

        # Context built per call, after pre-hooks, so it reflects facts recorded by earlier calls
        ctx = self.context_factory(session)

        # increase the number of call for the tool
        session.call_counts[tool_name] = session.call_counts.get(tool_name, 0) + 1

        # get retry policy
        retry_policy = self.retry_policies.get(tool_name, DEFAULT_RETRY_POLICY)

        # MAIN
        result = run_with_policy(
            tool_name,
            partial(_call_handler, tool_name, handler, ctx, tool_input),
            retry_policy,
            session.call_counts[tool_name],
        )

        # POST HOOKS
        self._run_post_hooks(tool_name, result, session)
        return result

    def _run_pre_hooks(self, tool_name: str, tool_input: dict, session: S) -> ToolResult | None:
        for hook in self.pre_hooks.get(tool_name, []):
            try:
                hook(tool_input, session)
            except ToolError as e:
                logger.info("   ⛔ %s blocked by %s: %s", tool_name, hook.__name__, e.message)
                return e.to_result()
            except Exception:
                logger.exception("   ! pre-hook %s crashed for %s", hook.__name__, tool_name)
                return {
                    "is_error": True,
                    "error_category": INTERNAL,
                    "is_retryable": False,
                    "content": {"message": f"{tool_name} could not be authorized due to an internal error."},
                }
        return None

    def _run_post_hooks(self, tool_name: str, result: ToolResult, session: S) -> None:
        for hook in self.post_hooks.get(tool_name, []):
            try:
                hook(result, session)
            except Exception:
                logger.exception("   ! post-hook %s crashed for %s", hook.__name__, tool_name)


def _call_handler[C](tool_name: str, handler: ToolHandler, ctx: C, tool_input: dict) -> ToolResult:
    try:
        return handler(ctx, **tool_input)
    except ToolError as e:
        return e.to_result()
    except TypeError as e:
        logger.warning("   ! %s called with invalid arguments: %s", tool_name, e)
        return {
            "is_error": True,
            "error_category": VALIDATION,
            "is_retryable": False,
            "content": {"message": f"Invalid arguments for {tool_name}: {e}"},
        }
    except TimeoutError:
        return {
            "is_error": True,
            "error_category": TRANSIENT,
            "is_retryable": True,
            "content": {"message": f"{tool_name} timed out. The result is unknown, not empty."},
        }
    except Exception:
        logger.exception("   ! %s crashed", tool_name)
        return {
            "is_error": True,
            "error_category": INTERNAL,
            "is_retryable": False,
            "content": {"message": f"{tool_name} failed due to an internal error."},
        }
