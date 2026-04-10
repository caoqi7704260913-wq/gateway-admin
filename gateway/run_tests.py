"""
运行测试脚本
"""
import os
os.environ['DEBUG'] = 'True'

if __name__ == '__main__':
    import sys
    sys.path.insert(0, 'd:\\python_project\\gateway')
    
    import pytest
    exit_code = pytest.main([
        'd:\\python_project\\gateway\\tests\\unit',
        '-v',
        '--tb=short'
    ])
    sys.exit(exit_code)
