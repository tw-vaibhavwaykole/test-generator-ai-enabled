import os
import sys
import logging
import pytest

def execute_tests():
    # Configure logging to output INFO-level messages
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    logger = logging.getLogger(__name__)

    # Define the path to the generated test code file
    test_file = "./output/plaintext_generated_test.py"
    
    # Check if the test file exists
    if not os.path.exists(test_file):
        logger.error("Test file not found at %s. Please run the code-generation module first to generate the test code.", test_file)
        sys.exit(1)
    
    logger.info("Executing generated test file: %s", test_file)
    
    # Run the test file using pytest
    result = pytest.main([test_file])
    
    if result == 0:
        logger.info("All tests passed successfully.")
    else:
        logger.error("Some tests failed. Exit code: %s", result)
    
    sys.exit(result)

if __name__ == "__main__":
    execute_tests()
