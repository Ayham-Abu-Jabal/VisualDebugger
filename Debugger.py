import sys
import copy
import types
import io
from typing import Any, Generator
from contextlib import contextmanager

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
        self.history: list[dict[str, Any]] = []
        self.max_steps: int = max_steps

    def trace_handler(self, frame: types.FrameType, event: str, arg: Any) -> Any:
        func_name = frame.f_code.co_name
        if func_name in ('trace_handler', 'safe_deepcopy', '__enter__', '__exit__'):
            return self.trace_handler

        if len(self.history) >= self.max_steps:
            return None

        if event == 'line':
            local_snapshot = {
                var_name: safe_deepcopy(val)
                for var_name, val in frame.f_locals.items()
                if not var_name.startswith('__')
            }
            
            self.history.append(frozendict({
                'function': func_name,
                'line': frame.f_lineno,
                'locals': local_snapshot
            }))
            
        return self.trace_handler

    def __enter__(self) -> 'ExecutionTracer':
        sys.settrace(self.trace_handler)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        sys.settrace(None)

if __name__ == "__main__":
    def calculate_basket(items: list[float]) -> float:
        total = 0.0
        tax_rate = 0.05
        for price in items:
            total += price + (price * tax_rate)
        return total

    with ExecutionTracer() as tracer:
        calculate_basket([100, 200])

    for step in tracer.history:
        print(f"Line {step['line']:<3} | Func: {step['function']:<16} | Locals: {step['locals']}")