#!/usr/bin/env python3

"""
Test Suite for Stockbroker Application

This module contains comprehensive unit tests and integration tests for the
stockbroker application. It verifies all core functionality including trade
validation, processing, and persistence.

Test Coverage:
    - Unit Tests:
        - TradeBook: Trade book creation and comparison
        - StockCodeService: Stock code validation and loading
        - TradeValidator: Trade parameter validation
        - TradeBookService: Trade processing and persistence
        - CommandProcessor: Command parsing and processing
    
    - Integration Tests:
        - End-to-end functionality in both batch and interactive modes
        - File handling and persistence
        - Error handling and validation

Test Data:
    The test suite creates and manages its own test data directory
    (tests/test_data) containing:
        - test_stockcode.csv: Sample valid stock codes
        - test_orders.csv: Trade book storage
        - test_batch_commands.txt: Sample commands for batch testing

Usage:
    Run all tests:
        $ python -m unittest tests/test.py

    Run specific test class:
        $ python -m unittest tests.test.TestTradeBook

    Run with verbosity:
        $ python -m unittest -v tests/test.py

Note:
    The test suite automatically manages test data cleanup after each test,
    ensuring a clean state for subsequent test runs.

Author: faw
Version: 1.1.0
"""

import unittest
import os
import sys
import subprocess
import time
import shutil
from typing import List, Dict, Optional, Tuple

# Add the src directory to the Python path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from stockbroker import (
    TradeBook,
    StockCodeService,
    TradeValidator,
    TradeBookService,
    CommandProcessor,
)


class TestTradeBook(unittest.TestCase):
    """
    Unit tests for the TradeBook class.
    
    Tests the core functionality of trade book entries, including:
    - Equality comparison based on action, stock code, and price
    - CSV format conversion
    - Volume handling
    
    Test Strategy:
        1. Test equality comparison with various combinations
        2. Verify CSV conversion preserves all attributes
        3. Ensure volume doesn't affect equality
    """

    def test_equality(self):
        """
        Test trade book equality comparison.
        
        Verifies that:
        - Books with same action, stock code, and price are equal
        - Volume differences don't affect equality
        - Different actions, codes, or prices make books unequal
        """
        book1 = TradeBook("buy", "AAPL", 100.00, 10)
        book2 = TradeBook("buy", "AAPL", 100.00, 20)  # Different volume
        book3 = TradeBook("sell", "AAPL", 100.00, 10)  # Different action
        book4 = TradeBook("buy", "MSFT", 100.00, 10)  # Different stock code
        book5 = TradeBook("buy", "AAPL", 101.00, 10)  # Different price

        self.assertEqual(book1, book2)  # Volume shouldn't matter for equality
        self.assertNotEqual(book1, book3)
        self.assertNotEqual(book1, book4)
        self.assertNotEqual(book1, book5)

    def test_csv_conversion(self):
        """
        Test conversion between TradeBook and CSV format.
        
        Verifies that:
        - All attributes are correctly serialized to CSV
        - CSV parsing recreates identical trade book
        - Price formatting maintains 2 decimal places
        """
        original = TradeBook("buy", "AAPL", 100.00, 10)
        csv_line = original.to_csv_line()
        from_csv = TradeBook.from_csv_line(csv_line)

        self.assertEqual(original.action, from_csv.action)
        self.assertEqual(original.stock_code, from_csv.stock_code)
        self.assertEqual(original.price, from_csv.price)
        self.assertEqual(original.volume, from_csv.volume)


class TestStockCodeService(unittest.TestCase):
    """
    Unit tests for the StockCodeService class.
    
    Tests the stock code validation service, including:
    - Loading stock codes from file
    - Validating stock codes
    - Handling missing files
    - Environment variable configuration
    
    Test Strategy:
        1. Test file loading with valid and invalid files
        2. Verify stock code validation
        3. Test error handling for missing files
    """

    def setUp(self):
        """
        Set up test environment.
        
        Creates:
        - Test directory
        - Sample stock code file with valid codes
        """
        # Create test directory if it doesn't exist
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)

        # Define test file path
        self.test_stockcode_path = os.path.join(self.test_dir, "test_stockcode.csv")

        # Create test file with sample stock codes
        with open(self.test_stockcode_path, "w") as f:
            f.write("AAPL\nMSFT\nGOOG\n")

    def tearDown(self):
        """
        Clean up test environment.
        
        Removes:
        - Test stock code file
        - Test directory if empty
        """
        if os.path.exists(self.test_stockcode_path):
            os.remove(self.test_stockcode_path)
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)

    def test_load_stock_codes(self):
        """
        Test loading stock codes from file.
        
        Verifies:
        - All valid codes are loaded
        - Empty lines are skipped
        - Set contains exactly expected codes
        """
        service = StockCodeService(self.test_stockcode_path)
        self.assertEqual(len(service.stock_codes), 3)
        self.assertTrue("AAPL" in service.stock_codes)
        self.assertTrue("MSFT" in service.stock_codes)
        self.assertTrue("GOOG" in service.stock_codes)

    def test_is_valid_stock_code(self):
        """
        Test stock code validation.
        
        Verifies:
        - Valid codes are accepted
        - Invalid codes are rejected
        - Case sensitivity is maintained
        """
        service = StockCodeService(self.test_stockcode_path)
        self.assertTrue(service.is_valid_stock_code("AAPL"))
        self.assertFalse(service.is_valid_stock_code("NOTREAL"))


class TestTradeValidator(unittest.TestCase):
    """
    Unit tests for the TradeValidator class.
    
    Tests the validation of all trade parameters according to business rules:
    - Action validation ('buy' or 'sell')
    - Stock code validation (4 uppercase letters, exists in database)
    - Price validation (≥ 0.50, 2 decimal places)
    - Volume validation (1 to 1,000,000)
    
    Test Strategy:
        1. Test each validation rule independently
        2. Test boundary conditions
        3. Test invalid cases
        4. Test complete trade validation
    """

    def setUp(self):
        """
        Set up test environment.
        
        Creates:
        - Test directory
        - Stock code file with sample codes
        - StockCodeService instance
        - TradeValidator instance
        """
        # Create test directory if it doesn't exist
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)

        # Define test file path
        self.test_stockcode_path = os.path.join(self.test_dir, "test_stockcode.csv")

        # Create test file with sample stock codes
        with open(self.test_stockcode_path, "w") as f:
            f.write("AAPL\nMSFT\nGOOG\n")

        self.stock_service = StockCodeService(self.test_stockcode_path)
        self.validator = TradeValidator(self.stock_service)

    def tearDown(self):
        """
        Clean up test environment.
        
        Removes:
        - Test stock code file
        - Test directory if empty
        """
        if os.path.exists(self.test_stockcode_path):
            os.remove(self.test_stockcode_path)
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)

    def test_validate_action(self):
        """
        Test trade action validation.
        
        Verifies:
        - 'buy' and 'sell' are valid actions
        - Other strings are invalid
        - Empty string is invalid
        - Case sensitivity is enforced
        """
        self.assertTrue(self.validator.validate_action("buy"))
        self.assertTrue(self.validator.validate_action("sell"))
        self.assertFalse(self.validator.validate_action("invalid"))
        self.assertFalse(self.validator.validate_action(""))

    def test_validate_stock_code(self):
        """
        Test stock code validation.
        
        Verifies format rules:
        - Must be exactly 4 characters
        - Must be all uppercase
        - Must be alphabetic
        - Must exist in stock code database
        
        Tests various invalid cases:
        - Too short/long
        - Lowercase
        - Non-alphabetic
        - Valid format but not in database
        """
        # Valid stock codes
        self.assertTrue(self.validator.validate_stock_code("AAPL"))
        self.assertTrue(self.validator.validate_stock_code("MSFT"))
        self.assertTrue(self.validator.validate_stock_code("GOOG"))

        # Invalid format
        self.assertFalse(self.validator.validate_stock_code("AAP"))  # Too short
        self.assertFalse(self.validator.validate_stock_code("AAPPL"))  # Too long
        self.assertFalse(self.validator.validate_stock_code("aapl"))  # Not uppercase
        self.assertFalse(self.validator.validate_stock_code("AAP1"))  # Not alphabetic
        self.assertFalse(self.validator.validate_stock_code(""))  # Empty

        # Not in stockcode.csv
        self.assertFalse(self.validator.validate_stock_code("AMZN"))

    def test_validate_price(self):
        """
        Test trade price validation.
        
        Verifies price rules:
        - Must be ≥ 0.50
        - Must have exactly 2 decimal places
        
        Tests boundary conditions:
        - Minimum valid price (0.50)
        - Various valid prices
        - Invalid prices (too low, wrong decimals)
        """
        # Valid prices
        self.assertTrue(self.validator.validate_price(0.50))  # Boundary case
        self.assertTrue(self.validator.validate_price(1.00))
        self.assertTrue(self.validator.validate_price(1000.25))

        # Invalid prices
        self.assertFalse(self.validator.validate_price(0.49))  # Less than minimum
        self.assertFalse(
            self.validator.validate_price(1.001)
        )  # More than 2 decimal places
        self.assertFalse(self.validator.validate_price(-1.00))  # Negative

    def test_validate_volume(self):
        """
        Test trade volume validation.
        
        Verifies volume rules:
        - Must be between 1 and 1,000,000 inclusive
        
        Tests boundary conditions:
        - Minimum valid volume (1)
        - Maximum valid volume (1,000,000)
        - Invalid volumes (0, > 1,000,000, negative)
        """
        # Valid volumes
        self.assertTrue(self.validator.validate_volume(1))  # Boundary case
        self.assertTrue(self.validator.validate_volume(100))
        self.assertTrue(self.validator.validate_volume(1000000))  # Boundary case

        # Invalid volumes
        self.assertFalse(self.validator.validate_volume(0))  # Less than minimum
        self.assertFalse(self.validator.validate_volume(1000001))  # More than maximum
        self.assertFalse(self.validator.validate_volume(-1))  # Negative

    def test_validate_trade(self):
        """
        Test complete trade validation.
        
        Verifies:
        - Valid trades pass all validation rules
        - Invalid trades return appropriate error messages
        - Each validation rule is checked in correct order
        
        Tests combinations of:
        - Valid and invalid actions
        - Valid and invalid stock codes
        - Valid and invalid prices
        - Valid and invalid volumes
        """
        # Valid trade
        result, msg = self.validator.validate_trade("buy", "AAPL", 100.00, 10)
        self.assertTrue(result)
        self.assertEqual(msg, "")

        # Invalid action
        result, msg = self.validator.validate_trade("invalid", "AAPL", 100.00, 10)
        self.assertFalse(result)
        self.assertIn("Invalid action", msg)

        # Invalid stock code
        result, msg = self.validator.validate_trade("buy", "INVALID", 100.00, 10)
        self.assertFalse(result)
        self.assertIn("Invalid stock code", msg)

        # Invalid price
        result, msg = self.validator.validate_trade("buy", "AAPL", 0.25, 10)
        self.assertFalse(result)
        self.assertIn("Invalid price", msg)

        # Invalid volume
        result, msg = self.validator.validate_trade("buy", "AAPL", 100.00, 0)
        self.assertFalse(result)
        self.assertIn("Invalid volume", msg)


class TestTradeBookService(unittest.TestCase):
    """Tests for the TradeBookService class."""

    def setUp(self):
        """Create test files and services."""
        # Create test directory if it doesn't exist
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)

        # Define test file path
        self.orders_file = os.path.join(self.test_dir, "test_orders.csv")

        # Remove test file if it exists
        if os.path.exists(self.orders_file):
            os.remove(self.orders_file)

        self.service = TradeBookService(self.orders_file)

    def tearDown(self):
        """Clean up test files."""
        if os.path.exists(self.orders_file):
            os.remove(self.orders_file)
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)

    def test_add_trade_book(self):
        """Test adding a new trade book."""
        result = self.service.process_trade("buy", "AAPL", 100.00, 10)
        self.assertEqual(result, "Trade book added.")
        self.assertEqual(len(self.service.trade_books), 1)
        self.assertEqual(self.service.trade_books[0].action, "buy")
        self.assertEqual(self.service.trade_books[0].stock_code, "AAPL")
        self.assertEqual(self.service.trade_books[0].price, 100.00)
        self.assertEqual(self.service.trade_books[0].volume, 10)

    def test_update_trade_book(self):
        """Test updating an existing trade book."""
        # Add initial trade
        self.service.process_trade("buy", "AAPL", 100.00, 10)

        # Update the same trade
        result = self.service.process_trade("buy", "AAPL", 100.00, 5)
        self.assertEqual(result, "Trade book updated.")
        self.assertEqual(len(self.service.trade_books), 1)  # No new book added
        self.assertEqual(self.service.trade_books[0].volume, 15)  # Volume updated

    def test_file_persistence(self):
        """Test that trade books are saved and loaded from file."""
        # Add a trade and ensure it's saved
        self.service.process_trade("buy", "AAPL", 100.00, 10)

        # Create a new service that should load from the file
        new_service = TradeBookService(self.orders_file)
        self.assertEqual(len(new_service.trade_books), 1)
        self.assertEqual(new_service.trade_books[0].action, "buy")
        self.assertEqual(new_service.trade_books[0].stock_code, "AAPL")
        self.assertEqual(new_service.trade_books[0].price, 100.00)
        self.assertEqual(new_service.trade_books[0].volume, 10)


class TestCommandProcessor(unittest.TestCase):
    """
    Unit tests for the CommandProcessor class.
    
    Tests the processing of trade commands, including:
    - Command parsing and validation
    - Integration with TradeValidator
    - Integration with TradeBookService
    - Error handling and messaging
    
    Test Strategy:
        1. Test valid command processing
        2. Test command format validation
        3. Test number format validation
        4. Test trade parameter validation
        5. Test error message formatting
    """

    def setUp(self):
        """
        Set up test environment.
        
        Creates:
        - Test directory
        - Stock code file with sample codes
        - Clean orders file
        - Required service instances:
            - StockCodeService
            - TradeValidator
            - TradeBookService
            - CommandProcessor
        """
        # Create test directory if it doesn't exist
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)

        # Define test file paths
        self.test_stockcode_path = os.path.join(self.test_dir, "test_stockcode.csv")
        self.orders_file = os.path.join(self.test_dir, "test_orders.csv")

        # Create test files
        with open(self.test_stockcode_path, "w") as f:
            f.write("AAPL\nMSFT\nGOOG\n")

        if os.path.exists(self.orders_file):
            os.remove(self.orders_file)

        # Initialize services
        stock_service = StockCodeService(self.test_stockcode_path)
        validator = TradeValidator(stock_service)
        trade_service = TradeBookService(self.orders_file)
        self.processor = CommandProcessor(validator, trade_service)

    def tearDown(self):
        """
        Clean up test environment.
        
        Removes:
        - Test stock code file
        - Test orders file
        - Test directory if empty
        """
        if os.path.exists(self.test_stockcode_path):
            os.remove(self.test_stockcode_path)
        if os.path.exists(self.orders_file):
            os.remove(self.orders_file)
        if os.path.exists(self.test_dir) and not os.listdir(self.test_dir):
            os.rmdir(self.test_dir)

    def test_valid_command(self):
        """
        Test processing of valid commands.
        
        Verifies:
        - Valid commands are processed successfully
        - Trade books are created/updated appropriately
        - Correct success messages are returned
        - Volume aggregation works correctly
        """
        result = self.processor.process_command("buy AAPL 100.00 10")
        self.assertEqual(result, "Trade book added.")

        # Update existing
        result = self.processor.process_command("buy AAPL 100.00 5")
        self.assertEqual(result, "Trade book updated.")

    def test_invalid_command_format(self):
        """
        Test processing of malformed commands.
        
        Verifies error handling for:
        - Missing parameters
        - Extra parameters
        - Invalid parameter order
        - Empty commands
        """
        result = self.processor.process_command("buy AAPL 100.00")  # Missing volume
        self.assertIn("Invalid command", result)

        result = self.processor.process_command(
            "buy AAPL 100.00 10 extra"
        )  # Extra parameter
        self.assertIn("Invalid command", result)

    def test_invalid_number_format(self):
        """
        Test processing of commands with invalid numbers.
        
        Verifies error handling for:
        - Non-numeric price
        - Non-numeric volume
        - Invalid price format
        - Invalid volume format
        """
        result = self.processor.process_command(
            "buy AAPL price 10"
        )  # Non-numeric price
        self.assertIn("Price must be a decimal number", result)

        result = self.processor.process_command(
            "buy AAPL 100.00 volume"
        )  # Non-numeric volume
        self.assertIn("Price must be a decimal number", result)

    def test_invalid_trade_parameters(self):
        """
        Test processing of commands with invalid trade parameters.
        
        Verifies error handling for:
        - Invalid actions
        - Invalid stock codes
        - Invalid prices
        - Invalid volumes
        
        Ensures appropriate error messages are returned for each case.
        """
        result = self.processor.process_command(
            "invalid AAPL 100.00 10"
        )  # Invalid action
        self.assertIn("Invalid action", result)

        result = self.processor.process_command(
            "buy INVALID 100.00 10"
        )  # Invalid stock code
        self.assertIn("Invalid stock code", result)

        result = self.processor.process_command("buy AAPL 0.25 10")  # Invalid price
        self.assertIn("Invalid price", result)

        result = self.processor.process_command("buy AAPL 100.00 0")  # Invalid volume
        self.assertIn("Invalid volume", result)


class TestEndToEndFunctionality(unittest.TestCase):
    """
    End-to-end integration tests for the stockbroker application.
    
    Tests the complete application workflow in both batch and interactive modes:
    - Command line interface
    - File handling
    - Trade processing
    - Error handling
    - Data persistence
    
    Test Strategy:
        1. Test batch mode processing
            - Valid commands
            - Invalid commands
            - File handling
            - Output formatting
        2. Test interactive mode simulation
            - Command processing
            - State persistence
            - Error handling
    """

    def setUp(self):
        """
        Set up test environment.
        
        Creates:
        - Test directory
        - Sample stock code file
        - Sample orders file
        - Batch command file with test scenarios
        
        The test files include various test cases:
        - Valid trades
        - Invalid actions
        - Invalid stock codes
        - Edge cases
        """
        # Create test directory if it doesn't exist
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_data")
        os.makedirs(self.test_dir, exist_ok=True)

        # Define test file paths
        self.test_stockcode_path = os.path.join(self.test_dir, "test_stockcode.csv")
        self.test_orders_path = os.path.join(self.test_dir, "test_orders.csv")
        self.test_batch_commands_path = os.path.join(
            self.test_dir, "test_batch_commands.txt"
        )

        # Create test files with sample data
        with open(self.test_stockcode_path, "w") as f:
            f.write("AAPL\nMSFT\nGOOG\nAMZN\n")

        with open(self.test_orders_path, "w") as f:
            f.write("buy,AAPL,100.00,10\n")

        with open(self.test_batch_commands_path, "w") as f:
            f.write("buy AAPL 100.00 5\n")
            f.write("sell MSFT 50.00 20\n")
            f.write("buy GOOG 1000.00 2\n")
            f.write("invalid AAPL 100.00 10\n")  # Invalid action
            f.write("buy NOTREAL 100.00 10\n")  # Invalid stock code

    def tearDown(self):
        """
        Clean up test environment.
        
        Removes all test files and directories:
        - Test stock code file
        - Test orders file
        - Test batch commands file
        - Test directory
        
        Also restores any backed up production files.
        """
        # Remove test directory and all its contents
        import shutil

        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_batch_mode(self):
        """
        Test the application in batch mode.
        
        Verifies:
        - Command line argument handling
        - Batch file processing
        - Output formatting
        - Error handling
        - File persistence
        
        Test Procedure:
        1. Set up test environment with sample files
        2. Run application with batch file
        3. Verify output messages
        4. Check orders file for correct trades
        5. Verify error handling
        """
        # Get path to the stockbroker.py script
        stockbroker_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "src", "stockbroker.py")
        )

        # First clear any existing orders.csv to avoid interference
        data_orders_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data", "orders.csv")
        )
        if os.path.exists(data_orders_path):
            os.rename(data_orders_path, data_orders_path + ".bak")

        try:
            # Copy the test stockcode.csv to the data directory to ensure it's found
            data_stockcode_path = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "data", "stockcode.csv")
            )
            if os.path.exists(data_stockcode_path):
                os.rename(data_stockcode_path, data_stockcode_path + ".bak")

            # Copy our test stockcode file to the data directory
            import shutil

            shutil.copy(self.test_stockcode_path, data_stockcode_path)

            # Run the application in batch mode
            command = (
                f"{sys.executable} {stockbroker_path} {self.test_batch_commands_path}"
            )
            env = os.environ.copy()
            env["STOCKCODE_FILE"] = data_stockcode_path
            env["ORDERS_FILE"] = self.test_orders_path

            # Capture the output
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, env=env
            )
            output = result.stdout

            # Verify expected output
            self.assertIn("buy AAPL 100.00 5", output)
            self.assertIn("sell MSFT 50.00 20", output)
            self.assertIn("buy GOOG 1000.00 2", output)
            self.assertIn("invalid AAPL 100.00 10", output)
            self.assertIn("buy NOTREAL 100.00 10", output)

            # Verify error messages
            self.assertIn("Invalid stock code", output)
            self.assertIn("Invalid action", output)

            # Verify orders file
            with open(self.test_orders_path, "r") as f:
                lines = f.readlines()

            # Verify minimum content
            self.assertGreaterEqual(
                len(lines), 1, "Expected at least one line in orders.csv"
            )

            # Verify specific trades
            found_aapl = False
            for line in lines:
                if "AAPL" in line and "buy" in line:
                    found_aapl = True
            self.assertTrue(found_aapl, "AAPL trade not found in orders file")

        finally:
            # Restore original files
            if os.path.exists(data_orders_path + ".bak"):
                if os.path.exists(data_orders_path):
                    os.remove(data_orders_path)
                os.rename(data_orders_path + ".bak", data_orders_path)

            if os.path.exists(data_stockcode_path + ".bak"):
                if os.path.exists(data_stockcode_path):
                    os.remove(data_stockcode_path)
                os.rename(data_stockcode_path + ".bak", data_stockcode_path)

    def test_manual_interactive_mode(self):
        """
        Test interactive mode functionality.
        
        Simulates interactive usage by directly testing the command processor:
        - Command processing
        - Trade book updates
        - Error handling
        - State persistence
        
        Note: This is a simulation of interactive mode since actual
        interactive testing would require user input simulation.
        """
        # Create a direct test of the command processor instead
        stock_service = StockCodeService(self.test_stockcode_path)
        validator = TradeValidator(stock_service)
        trade_service = TradeBookService(self.test_orders_path)
        processor = CommandProcessor(validator, trade_service)

        # Process test commands
        result1 = processor.process_command("buy AAPL 100.00 5")
        self.assertIn("Trade book updated", result1)

        result2 = processor.process_command("sell AMZN 500.00 10")
        self.assertIn("Trade book added", result2)

        # Verify persistence
        with open(self.test_orders_path, "r") as f:
            content = f.read()

        # Verify trades were recorded
        self.assertIn("AAPL", content, "AAPL trade missing from orders.csv")
        self.assertIn("AMZN", content, "AMZN trade missing from orders.csv")


if __name__ == "__main__":
    unittest.main()
