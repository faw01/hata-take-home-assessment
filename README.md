# Overview

A stockbroker needs to keep track of trade coming from investors and record them to trade books. If there is any existing trade book for any incoming order, then the stockbroker needs to increase or decrease the volume of the order. If there's no existing trade book, then the stockbroker needs to create one.

A trade book is a record entry, which has the following data:
- Trade action (buy or sell)
- A stock code
- Trade price
- The volume of the trade

# Problem Statement

Create a command-line application to record incoming trade from investors. To record an order via a command line, a user shall issue a command with parameters of action of the trade (it is either **buy** or **sell**), the **stock code**, the **price** of the trade, and the **volume** of the trade.

On receiving a trade, the application shall check whether any existing trade book for that stock code with the same trade action and trade price. If there is, then the application will adjust the volume of the trade book of that stock code. The adjustment shall be made depending on the incoming trade action and its volume.

If the application does not find any trade book with the same stock code, trade action, and trade price, then the application will create a new trade book. If the stock code supplied is not valid, it will reject the trade order. A valid stock code means that a stock code can be found in a file `stockcode.csv` file, as explained below.

The application can be executed in two modes. The first mode, called the interactive mode, is when the command line application is invoked without a parameter. When the application is invoked, it will show a character "$" as a prompt waiting for user input. The application will exit if it receives a command "exit" on the prompt.

The second mode is when the application is invoked with 1 parameter. The parameter is a file path location to a text file, where the application shall read and process the text file line by line. Each line contains the trade order separated by a space character.

The application persists the data into files. The application shall read two files, `stockcode.csv` and `orders.csv`. The application shall read the files on start-up. The file `stockcode.csv` contains all the valid stock codes, one stock code per line. The file `orders.csv` contains trade orders, one trade book per line. That means each line has the trade action, stock code, trade price, and trade volume, separated by commas.

A sample of 2 lines in file stockcode.csv:
```
AAPL
GOOGL
```

A sample of 2 lines in file orders.csv:
```
buy,AAPL,1000.00,100
sell,AAPL,1000.10,10
```

# Constraints

- Stock code is a 4 letter code.
- Stock code is all upper case.
- A trade price is a number with 2 decimal points, with a minimum of 0.50.
- A trade volume is a number between 1 to 1,000,000.
- The application must be invoked by calling stockbroker.sh Linux shell, or stockbroker.bat on Windows.

# Example

Example of invoking the application by supplying a file path to read:

```
>./stockbroker.sh orders.txt
```

Example of executing the application in an interactive mode:

```
>./stockbroker.sh
$
```

Example of a trade that is input via a command line:

```
$ buy AAPL 1000.00 100
Trade book added.
```

Where **buy** is the trade action, **AAPL** is the stock code, **1000.00** is the trade price, and finally, **100** is the volume of the trade.