"""
测试套件入口

运行所有测试：
    python -m pytest tests/ -v

或运行单个测试：
    python tests/test_short_term.py
"""

import pytest
import sys


def run_all_tests():
    """运行所有测试"""
    return pytest.main([
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ])


def run_specific_test(test_name):
    """运行指定测试"""
    return pytest.main([
        f"tests/{test_name}",
        "-v",
        "--tb=short"
    ])


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        exit_code = run_specific_test(test_name)
    else:
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
