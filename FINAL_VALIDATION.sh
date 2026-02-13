#!/bin/bash
echo "==================================================================="
echo "FINAL VALIDATION REPORT"
echo "==================================================================="
echo ""

echo "1. TESTING SUITE"
echo "-------------------------------------------------------------------"
python -m pytest tests -v --tb=short 2>&1 | tail -3
echo ""

echo "2. TYPE CHECKING (Core Modules)"
echo "-------------------------------------------------------------------"
mypy thalos_prime tests tools --strict --show-error-codes --no-implicit-optional 2>&1 | grep "^Found"
echo ""

echo "3. SYNTAX CHECK"
echo "-------------------------------------------------------------------"
python -m py_compile thalos_prime/*.py 2>&1 && echo "✅ No syntax errors" || echo "❌ Syntax errors found"
echo ""

echo "4. IMPORT CHECK"
echo "-------------------------------------------------------------------"
python -c "import thalos_prime; print('✅ Main package imports successfully')" 2>&1
python -c "from thalos_prime import BabelGenerator, BabelEnumerator, BabelDecoder; print('✅ Core classes import successfully')" 2>&1
python -c "from thalos_prime import deep_synthesis; print('✅ Synthesis module imports successfully')" 2>&1
echo ""

echo "5. FILE COMPLETENESS CHECK"
echo "-------------------------------------------------------------------"
EMPTY_FILES=$(find thalos_prime tests -name "*.py" -size 0 2>/dev/null)
if [ -z "$EMPTY_FILES" ]; then
    echo "✅ No empty Python files found"
else
    echo "❌ Empty files found:"
    echo "$EMPTY_FILES"
fi
echo ""

echo "6. GIT STATUS"
echo "-------------------------------------------------------------------"
git status --short
echo ""

echo "==================================================================="
echo "VALIDATION COMPLETE"
echo "==================================================================="
