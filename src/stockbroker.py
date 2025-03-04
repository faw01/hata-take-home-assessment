#!/usr/bin/env python3

"""
Stockbroker Application

This module implements a stock trading application that processes buy and sell orders
for stocks. It supports both interactive and batch processing modes, validates trade
parameters, and maintains a persistent record of trades.

Features:
    - Process buy and sell orders for stocks
    - Validate stock codes against a predefined list
    - Enforce trading rules (price, volume limits)
    - Maintain trade books with aggregated volumes
    - Support both interactive and batch processing modes

Usage:
    Interactive mode:
        $ ./stockbroker.sh
        $ buy AAPL 150.00 100
        Trade book added.

    Batch mode:
        $ ./stockbroker.sh orders.txt

Trading Rules:
    - Stock codes must be 4 uppercase letters
    - Price must be a number with 2 decimal places, minimum 0.50
    - Volume must be between 1 and 1,000,000
    - Stock code must exist in stockcode.csv

File Structure:
    - stockcode.csv: List of valid stock codes
    - orders.csv: Persistent storage of trade books

Author: faw
Version: 1.1.0
"""

import os
import sys
from typing import List, Dict, Optional, Tuple


class TradeBook:
    """
    Represents a trade book entry that records stock trading activities.
    
    A trade book maintains information about a specific trade action (buy/sell)
    for a particular stock at a given price, along with the total volume.
    Multiple trades with the same action, stock code, and price are aggregated
    by summing their volumes.

    Attributes:
        action (str): The trade action ('buy' or 'sell')
        stock_code (str): The 4-letter stock code (e.g., 'AAPL')
        price (float): The trade price with 2 decimal places
        volume (int): The total volume of shares traded

    Example:
        >>> trade = TradeBook('buy', 'AAPL', 150.00, 100)
        >>> trade.to_csv_line()
        'buy,AAPL,150.00,100'
    """

    def __init__(self, action: str, stock_code: str, price: float, volume: int):
        """
        Initialize a new trade book entry.

        Args:
            action: The trade action ('buy' or 'sell')
            stock_code: The stock code (4 uppercase letters)
            price: The trade price (≥ 0.50, 2 decimal places)
            volume: The number of shares (1 to 1,000,000)
        """
        self.action = action
        self.stock_code = stock_code
        self.price = price
        self.volume = volume

    def __eq__(self, other) -> bool:
        """
        Compare two trade books for equality.
        
        Trade books are considered equal if they have the same action,
        stock code, and price. Volume is not considered for equality
        as it can be aggregated.

        Args:
            other: Another TradeBook instance to compare with

        Returns:
            bool: True if the trade books are equal, False otherwise
        """
        if not isinstance(other, TradeBook):
            return False
        return (
            self.action == other.action
            and self.stock_code == other.stock_code
            and self.price == other.price
        )

    def __hash__(self) -> int:
        """
        Generate a hash value for the trade book.
        
        The hash is based on the action, stock code, and price,
        matching the equality comparison behavior.

        Returns:
            int: Hash value for the trade book
        """
        return hash((self.action, self.stock_code, self.price))

    def to_csv_line(self) -> str:
        """
        Convert the trade book to a CSV line format.
        
        Returns:
            str: CSV formatted string with action, stock code, price, and volume
        """
        return f"{self.action},{self.stock_code},{self.price:.2f},{self.volume}"

    @staticmethod
    def from_csv_line(line: str) -> "TradeBook":
        """
        Create a TradeBook instance from a CSV line.
        
        Args:
            line: CSV formatted string containing trade book data

        Returns:
            TradeBook: New trade book instance

        Raises:
            ValueError: If the CSV line format is invalid
        """
        action, stock_code, price, volume = line.strip().split(",")
        return TradeBook(action, stock_code, float(price), int(volume))


class StockCodeService:
    """
    Service for managing and validating stock codes.
    
    This service loads valid stock codes from a CSV file and provides
    validation functionality. Stock codes must be 4 uppercase letters
    and exist in the stockcode.csv file.

    The service supports environment variable configuration for the
    stock code file path through 'STOCKCODE_FILE'.

    Attributes:
        filename (str): Path to the stock code CSV file
        stock_codes (set[str]): Set of valid stock codes
    """

    def __init__(self, filename: str = None):
        """
        Initialize the stock code service.

        Args:
            filename: Optional path to stock code file
                     (defaults to STOCKCODE_FILE env var or 'data/stockcode.csv')
        """
        # Use environment variable if set, otherwise use default path
        self.filename = filename or os.environ.get(
            "STOCKCODE_FILE", "data/stockcode.csv"
        )
        self.stock_codes = set()
        self.load_stock_codes()

    def load_stock_codes(self) -> None:
        """
        Load stock codes from the CSV file.
        
        Reads the stock code file and populates the stock_codes set.
        Empty lines are skipped. If the file is not found, a warning
        is printed and an empty set is used.
        """
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    stock_code = line.strip()
                    if stock_code:  # Skip empty lines
                        self.stock_codes.add(stock_code)
        except FileNotFoundError:
            print(f"Warning: Stock code file '{self.filename}' not found.")
            self.stock_codes = set()

    def is_valid_stock_code(self, stock_code: str) -> bool:
        """
        Check if a stock code is valid.
        
        A stock code is valid if it exists in the loaded stock_codes set.

        Args:
            stock_code: The stock code to validate

        Returns:
            bool: True if the stock code is valid, False otherwise
        """
        return stock_code in self.stock_codes


class TradeValidator:
    """
    Validates trade parameters according to business rules.
    
    This class implements validation logic for all aspects of a trade:
    - Action must be 'buy' or 'sell'
    - Stock code must be 4 uppercase letters and exist in stockcode.csv
    - Price must be ≥ 0.50 with exactly 2 decimal places
    - Volume must be between 1 and 1,000,000

    The validator works in conjunction with StockCodeService to ensure
    stock codes are valid.
    """

    def __init__(self, stock_code_service: StockCodeService):
        """
        Initialize the trade validator.

        Args:
            stock_code_service: Service for validating stock codes
        """
        self.stock_code_service = stock_code_service

    def validate_action(self, action: str) -> bool:
        """
        Validate the trade action.
        
        Args:
            action: The trade action to validate

        Returns:
            bool: True if action is 'buy' or 'sell', False otherwise
        """
        return action in ["buy", "sell"]

    def validate_stock_code(self, stock_code: str) -> bool:
        """
        Validate the stock code format and existence.
        
        A valid stock code must:
        - Be exactly 4 characters long
        - Contain only uppercase letters
        - Exist in the stock code service's database

        Args:
            stock_code: The stock code to validate

        Returns:
            bool: True if the stock code is valid, False otherwise
        """
        if not stock_code or len(stock_code) != 4:
            return False

        if not stock_code.isupper() or not stock_code.isalpha():
            return False

        return self.stock_code_service.is_valid_stock_code(stock_code)

    def validate_price(self, price: float) -> bool:
        """
        Validate the trade price.
        
        A valid price must:
        - Be greater than or equal to 0.50
        - Have exactly 2 decimal places

        Args:
            price: The price to validate

        Returns:
            bool: True if the price is valid, False otherwise
        """
        return price >= 0.50 and round(price, 2) == price

    def validate_volume(self, volume: int) -> bool:
        """
        Validate the trade volume.
        
        A valid volume must be between 1 and 1,000,000 inclusive.

        Args:
            volume: The volume to validate

        Returns:
            bool: True if the volume is valid, False otherwise
        """
        return 1 <= volume <= 1000000

    def validate_trade(
        self, action: str, stock_code: str, price: float, volume: int
    ) -> Tuple[bool, str]:
        """
        Validate all trade parameters.
        
        This method performs comprehensive validation of all trade parameters
        and returns both a success indicator and an error message if validation
        fails.

        Args:
            action: The trade action ('buy' or 'sell')
            stock_code: The stock code (4 uppercase letters)
            price: The trade price (≥ 0.50, 2 decimal places)
            volume: The number of shares (1 to 1,000,000)

        Returns:
            Tuple[bool, str]: (True, "") if valid, (False, error_message) if invalid
        """
        if not self.validate_action(action):
            return False, "Invalid action. Must be 'buy' or 'sell'."

        if not self.validate_stock_code(stock_code):
            msg = (
                "Invalid stock code. Must be 4 uppercase letters "
                "and exist in stockcode.csv."
            )
            return False, msg

        if not self.validate_price(price):
            msg = "Invalid price. Must be a number with 2 decimal places and >= 0.50."
            return False, msg

        if not self.validate_volume(volume):
            return False, "Invalid volume. Must be between 1 and 1,000,000."

        return True, ""


class TradeBookService:
    """
    Service for managing trade books.
    
    This service handles the persistence and retrieval of trade books,
    including:
    - Loading existing trade books from CSV
    - Saving trade books to CSV
    - Finding existing trade books
    - Processing new trades by updating or creating trade books

    Trade books with the same action, stock code, and price are aggregated
    by summing their volumes.

    The service supports environment variable configuration for the
    orders file path through 'ORDERS_FILE'.
    """

    def __init__(self, filename: str = None):
        """
        Initialize the trade book service.

        Args:
            filename: Optional path to orders file
                     (defaults to ORDERS_FILE env var or 'data/orders.csv')
        """
        self.filename = filename or os.environ.get("ORDERS_FILE", "data/orders.csv")
        self.trade_books: List[TradeBook] = []
        self.load_trade_books()

    def load_trade_books(self) -> None:
        """
        Load trade books from the CSV file.
        
        Reads existing trade books from the orders file. If the file
        doesn't exist, starts with an empty list.
        """
        try:
            with open(self.filename, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:  # Skip empty lines
                        self.trade_books.append(TradeBook.from_csv_line(line))
        except FileNotFoundError:
            # It's okay if the file doesn't exist yet
            self.trade_books = []

    def save_trade_books(self) -> None:
        """
        Save trade books to the CSV file.
        
        Creates the directory if it doesn't exist and writes all
        trade books to the file in CSV format.
        """
        # Create directory if it doesn't exist
        directory = os.path.dirname(self.filename)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            
        with open(self.filename, "w") as file:
            for trade_book in self.trade_books:
                file.write(trade_book.to_csv_line() + "\n")

    def find_trade_book(
        self, action: str, stock_code: str, price: float
    ) -> Optional[TradeBook]:
        """
        Find a trade book with matching parameters.
        
        Searches for an existing trade book with the same action,
        stock code, and price. Volume is not considered in the match.

        Args:
            action: The trade action to match
            stock_code: The stock code to match
            price: The price to match

        Returns:
            Optional[TradeBook]: Matching trade book or None if not found
        """
        search_book = TradeBook(action, stock_code, price, 0)
        for trade_book in self.trade_books:
            if trade_book == search_book:
                return trade_book
        return None

    def process_trade(
        self, action: str, stock_code: str, price: float, volume: int
    ) -> str:
        """
        Process a trade by updating or creating a trade book.
        
        If a matching trade book exists (same action, stock code, price),
        updates its volume. Otherwise, creates a new trade book.

        Args:
            action: The trade action ('buy' or 'sell')
            stock_code: The stock code
            price: The trade price
            volume: The number of shares

        Returns:
            str: Success message indicating whether a book was updated or added
        """
        existing_book = self.find_trade_book(action, stock_code, price)

        if existing_book:
            existing_book.volume += volume
            self.save_trade_books()
            return "Trade book updated."
        else:
            new_book = TradeBook(action, stock_code, price, volume)
            self.trade_books.append(new_book)
            self.save_trade_books()
            return "Trade book added."


class CommandProcessor:
    """
    Processes trade commands and coordinates validation and execution.
    
    This class acts as the main coordinator between the trade validator
    and trade book service. It:
    - Parses command strings
    - Validates trade parameters
    - Processes valid trades
    - Provides appropriate feedback messages

    Command Format:
        [buy|sell] [STOCKCODE] [PRICE] [VOLUME]
        Example: "buy AAPL 150.00 100"
    """

    def __init__(
        self, trade_validator: TradeValidator, trade_book_service: TradeBookService
    ):
        """
        Initialize the command processor.

        Args:
            trade_validator: Validator for trade parameters
            trade_book_service: Service for processing trades
        """
        self.trade_validator = trade_validator
        self.trade_book_service = trade_book_service

    def process_command(self, command: str) -> str:
        """
        Process a trade command string.
        
        Parses the command, validates all parameters, and if valid,
        processes the trade.

        Args:
            command: The command string to process

        Returns:
            str: Result message indicating success or describing the error
        """
        # Split the command by spaces
        parts = command.strip().split()

        # Check if we have the right number of parts
        if len(parts) != 4:
            return "Invalid command. Format: [buy|sell] [STOCKCODE] [PRICE] [VOLUME]"

        action, stock_code, price_str, volume_str = parts

        # Parse price and volume
        try:
            price = float(price_str)
            volume = int(volume_str)
        except ValueError:
            return (
                "Invalid command. Price must be a decimal number "
                "and volume must be an integer."
            )

        # Validate the trade
        is_valid, error_message = self.trade_validator.validate_trade(
            action, stock_code, price, volume
        )
        if not is_valid:
            return error_message

        # Process the trade
        return self.trade_book_service.process_trade(action, stock_code, price, volume)


def interactive_mode(command_processor: CommandProcessor) -> None:
    """
    Run the application in interactive mode.
    
    Provides a command prompt where users can enter trade commands
    one at a time. Type 'exit' to quit.

    Args:
        command_processor: The command processor to handle trades
    """
    while True:
        try:
            command = input("$ ")
            if command.lower() == "exit":
                break

            if command.strip():
                result = command_processor.process_command(command)
                print(result)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {str(e)}")


def batch_mode(command_processor: CommandProcessor, filename: str) -> None:
    """
    Run the application in batch mode.
    
    Processes multiple trade commands from a file, one per line.

    Args:
        command_processor: The command processor to handle trades
        filename: Path to the file containing trade commands
    """
    try:
        with open(filename, "r") as file:
            for line in file:
                line = line.strip()
                if line:
                    result = command_processor.process_command(line)
                    print(f"{line}")
                    print(f"{result}")
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
    except Exception as e:
        print(f"Error: {str(e)}")


def main() -> None:
    """
    Main entry point for the application.
    
    Initializes all required services and determines whether to run
    in interactive or batch mode based on command line arguments.
    
    Interactive Mode:
        $ ./stockbroker.sh
    
    Batch Mode:
        $ ./stockbroker.sh orders.txt
    """
    # Initialize services
    stock_code_service = StockCodeService()
    trade_validator = TradeValidator(stock_code_service)
    trade_book_service = TradeBookService()
    command_processor = CommandProcessor(trade_validator, trade_book_service)

    # Determine mode of operation
    if len(sys.argv) > 1:
        # Batch mode
        batch_mode(command_processor, sys.argv[1])
    else:
        # Interactive mode
        interactive_mode(command_processor)


if __name__ == "__main__":
    main()
