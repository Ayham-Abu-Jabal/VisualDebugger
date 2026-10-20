import sys
import copy
import types
import io
from typing import Any
from types import MappingProxyType
from deepdiff import DeepDiff

def safe_deepcopy(obj: Any) -> Any:
    uncopyable_types = (
        types.ModuleType, 
        types.FunctionType, 
        types.MethodType, 
        io.IOBase,
    )
    if isinstance(obj, uncopyable_types):
        return f"<Uncopyable: {type(obj).__name__}>"
    
    try:
        return copy.deepcopy(obj)
    except (TypeError, ValueError):
        return f"<Uncopyable/Error: {type(obj).__name__}>"

class ExecutionTracer:
    def __init__(self, max_steps: int = 10000) -> None:
        self.history: list[MappingProxyType[str, Any]] = []
        self.max_steps: int = max_steps
        self._prev_locals: dict[str, Any] = {}

    def trace_handler(self, frame: types.FrameType, event: str, arg: Any) -> Any:
        func_name = frame.f_code.co_name
        if func_name in ('trace_handler', 'safe_deepcopy', '__enter__', '__exit__'):
            return self.trace_handler

        if len(self.history) >= self.max_steps:
            return None

        if event == 'line':
            current_locals = {
                var_name: safe_deepcopy(val)
                for var_name, val in frame.f_locals.items()
                if not var_name.startswith('__')
            }
            
            if not self.history:
                diff_data = {"event_type": "INITIAL", "details": "Initial scope capture", "locals": current_locals}
                self.history.append(MappingProxyType({
                    'function': func_name,
                    'line': frame.f_lineno,
                    'diff': diff_data
                }))
            else:
                diff_result = DeepDiff(self._prev_locals, current_locals, ignore_order=True)
                if diff_result:
                    diff_dict = diff_result.to_dict()
                    
                    if diff_dict:
                        diff_data = {"event_type": "MUTATION", "changes": diff_dict}
                        self.history.append(MappingProxyType({
                            'function': func_name,
                            'line': frame.f_lineno,
                            'diff': diff_data
                        }))
            
            self._prev_locals = current_locals
            
        return self.trace_handler

    def __enter__(self) -> 'ExecutionTracer':
        sys.settrace(self.trace_handler)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        sys.settrace(None)

