import os
from cs50 import SQL
import sqlite3
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
# from flask_Session.__init__ import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
# app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
# db = SQL("sqlite:///finance.db")

db = SQL("postgres://fjxwxmltbneqra:14048b76e9edb786a84cf371825f7be1c61225e1cbf61bdfd1c2846a2f09e7fc@ec2-35-168-54-239.compute-1.amazonaws.com:5432/d3m16sv2qdmmpr")
# conn = sqlite3.connect('finance.db')
# db = conn.cursor()

# Make sure API key is set if not 
#    os.environ.get("API_KEY"):
#    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    # query database for session id
    rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    cash = rows[0]["cash"]
    id = rows[0]["id"]

    # create new tables to record stock purchases
    db.execute("CREATE TABLE IF NOT EXISTS current (id integer, stock_name text, symbol text, price numeric, shares integer, total numeric)")
    db.execute("CREATE TABLE IF NOT EXISTS history (id integer, symbol text, shares integer, price numeric, date text)")

    # update to current stock price
    update = db.execute("SELECT * FROM current WHERE id = :id", id=id)
    for i in range(len(update)):
        current = lookup(update[i]["symbol"])
        symbol = current["symbol"]
        price = current["price"]
        total = current["price"]*int(update[i]["shares"])
        db.execute("UPDATE current SET price = :price, total = :total WHERE id = :id AND symbol = :symbol", price=price, total=total, id=id, symbol=symbol)

    # select stocks and convert to usd for index table
    stocks = db.execute("SELECT * FROM current WHERE id = :id", id=id)
    current_total = cash

    for i in range(len(stocks)):
        current_total = current_total + float(stocks[i]["total"])
        stocks[i]["price"] = usd(stocks[i]["price"])
        stocks[i]["total"] = usd(stocks[i]["total"])

    cash = usd(cash)
    current_total = usd(current_total)

    # Show index table
    return render_template("index.html", stocks=stocks, cash=cash, curent_total=current_total)


@app.route("/addcash", methods=["GET", "POST"])
@login_required
def addcash():
    """Add Cash"""

    # query database for session id
    rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
    cash = rows[0]["cash"]
    id = rows[0]["id"]

    if request.method == "POST":

         # Ensure cash amt was submitted
        if not request.form.get("cash"):
            return apology("must provide a valid amount", 406)

        if request.form.get("cash").isalpha():
            return apology("must provide a valid amount", 406)

        if int(request.form.get("cash")) <= 0:
            return apology("must provide a valid amount", 406)

        # Add cash to db
        cash = cash + float(request.form.get("cash"))
        db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=id)

        price = request.form.get("cash")
        symbol = "CASH"
        shares = 1
        timestamp = datetime.now()

        db.execute("INSERT INTO history (id, symbol, shares, price, date) VALUES (:id, :symbol, :shares, :price, :date)", id=id,  symbol=symbol, shares=shares, price=price, date=timestamp)

        # update to current stock prices
        update = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        for i in range(len(update)):
            current = lookup(update[i]["symbol"])
            symbol = current["symbol"]
            price = current["price"]
            total = current["price"]*int(update[i]["shares"])
            db.execute("UPDATE current SET price = :price, total = :total WHERE id = :id AND symbol = :symbol", price=price, total=total, id=id, symbol=symbol)

        # select stocks and convert to usd for index table
        stocks = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        current_total = cash

        for i in range(len(stocks)):
            current_total = current_total + float(stocks[i]["total"])
            stocks[i]["price"] = usd(stocks[i]["price"])
            stocks[i]["total"] = usd(stocks[i]["total"])

        cash = usd(cash)
        current_total = usd(current_total)

        # Show index table
        return render_template("index.html", stocks=stocks, cash=cash, curent_total=current_total)

    else:
        cash = usd(cash)
        return render_template("addcash.html",  cash=cash)



@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    # query database for session id
    users = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])

    cash = users[0]["cash"]
    id = session["user_id"]

    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a valid stock symbol", 404)

        # lookup current stock price
        stocks = lookup(request.form.get("symbol"))

        # ensure symbol was valid
        if not stocks:
            return apology("must provide a valid stock symbol", 404)

        # Ensure shares entered was positive integer
        if not request.form.get("shares"):
            return apology("number of shares must be a positive integer", 405)

        if request.form.get("shares").isalpha():
            return apology("number of shares must be a positive integer", 405)

        # Ensure shares entered was positive integer
        if int(request.form.get("shares")) <= 0:
            return apology("number of shares must be a positive integer", 405)


        price = stocks["price"]
        shares = request.form.get("shares")
        timestamp = datetime.now()

        # calculate current share hold total
        total = int(shares) * float(price)

        # check if user has enough cash to purchase
        if total > float(cash):
            return apology("you don't have enough cash for that", 402)

        # update cash
        else:
            cash = cash - total

        # update tables with purchased stock
        db.execute("UPDATE users SET cash = :cash WHERE id = :user_id", cash=cash, user_id=id)
        db.execute("INSERT INTO history (id, symbol, shares, price, date) VALUES (:id, :symbol, :shares, :price, :date)", id=id,  symbol=stocks["symbol"], shares=shares, price=price, date=timestamp)

        # check if user already owns other shares of this stock
        check = db.execute("SELECT * from current WHERE id = :id AND symbol = :symbol", id=id, symbol=stocks["symbol"])
        if len(check) != 0 :
            for i in range(len(check)):
                shares = int(check[i]["shares"]) + int(shares)

            total = shares * price
            db.execute("UPDATE current SET price = :price, shares = :shares, total= :total WHERE id = :id AND symbol = :symbol", price=price, shares=shares, total=total, id=id, symbol=stocks["symbol"])
        else:
            db.execute("INSERT INTO current (id, stock_name, symbol, price, shares, total) VALUES (:id, :stock_name, :symbol, :price, :shares,  :total)", id=id, stock_name=stocks["name"], symbol=stocks["symbol"], price=price, shares=shares, total=total)


        # update to current stock prices
        update = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        for i in range(len(update)):
            current = lookup(update[i]["symbol"])
            symbol = current["symbol"]
            price = current["price"]
            total = current["price"]*int(update[i]["shares"])
            db.execute("UPDATE current SET price = :price, total = :total WHERE id = :id AND symbol = :symbol", price=price, total=total, id=id, symbol=symbol)

        # select stocks and convert to usd for index table
        stocks = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        current_total = cash

        for i in range(len(stocks)):
            current_total = current_total + float(stocks[i]["total"])
            stocks[i]["price"] = usd(stocks[i]["price"])
            stocks[i]["total"] = usd(stocks[i]["total"])

        cash = usd(cash)
        current_total = usd(current_total)

         # Show index table
        return render_template("index.html", stocks=stocks, cash=cash, curent_total=current_total)

    else:
        cash = usd(users[0]["cash"])
        return render_template("buy.html", cash=cash)


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    id = session["user_id"]

    # select from db to show on page
    history = db.execute("SELECT * FROM history WHERE id = :id", id=id)

    # change any floats to USD
    for i in range(len(history)):
        history[i]["price"] = usd(history[i]["price"])

    # return to history page with all history
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a valid stock symbol", 404)

        stocks = lookup(request.form.get("symbol"))

        if not stocks:
            return apology("must provide a valid stock symbol", 404)

        # Show current price of stock requested
        return render_template("quoted.html", name=stocks["name"], symbol=stocks["symbol"], price=stocks["price"])

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Ensure passwords match
        elif request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        # Query database for username
        check = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(check) != 0 :
                return apology("that username is taken", 403)

        # Hash pw
        hash = generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)

        # Add new user to db
        db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)", username=request.form.get("username"), hash=hash)

        # Redirect user to login
        return render_template("login.html")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    # query database for session id
    users = db.execute("SELECT * FROM users WHERE id = :user_id", user_id=session["user_id"])

    cash = users[0]["cash"]
    id = session["user_id"]

    if request.method == "POST":

        # Ensure symbol was submitted
        if not request.form.get("symbol"):
            return apology("must provide a valid stock symbol", 404)

        # lookup current stock price
        stocks = lookup(request.form.get("symbol"))

        # ensure symbol was valid
        if not stocks:
            return apology("must provide a valid stock symbol", 404)

        # Ensure shares entered was positive integer
        if request.form.get("shares").isalpha():
            return apology("number of shares must be a positive integer", 405)

        if int(request.form.get("shares")) <= 0:
            return apology("number of shares must be a positive integer", 405)


        price = stocks["price"]
        shares = request.form.get("shares")
        history_shares = -int(shares)
        timestamp = datetime.now()
        total = int(shares) * float(price)
        cash = cash + total

        # check if user has that stock to sell, if so update cash and current table
        check = db.execute("SELECT * from current WHERE id = :id AND symbol = :symbol", id=id, symbol=stocks["symbol"])
        if len(check) != 0 :
            for i in range(len(check)):
                if int(check[i]["shares"]) < int(shares):
                    return apology("you don't have that many shares to sell",  401)
                shares = int(check[i]["shares"]) - int(shares)

            db.execute("UPDATE current SET price = :price, shares = :shares, total= :total WHERE id = :id AND symbol = :symbol", price=price, shares=shares, total=total, id=id, symbol=stocks["symbol"])
            db.execute("UPDATE users SET cash = :cash WHERE id = :id", cash=cash, id=id)

        else:
            return apology("you don't have those shares to sell", 401)

        # update history table with sold stock
        db.execute("INSERT INTO history (id, symbol, shares, price, date) VALUES (:id, :symbol, :shares, :price, :date)", id=id,  symbol=stocks["symbol"], shares=history_shares, price=price, date=timestamp)

        # delete row from table is shares is now 0
        db.execute("DELETE FROM current WHERE shares = 0")

        # update to current stock prices
        update = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        for i in range(len(update)):
            current = lookup(update[i]["symbol"])
            symbol = current["symbol"]
            price = current["price"]
            total = current["price"]*int(update[i]["shares"])
            db.execute("UPDATE current SET price = :price, total = :total WHERE id = :id AND symbol = :symbol", price=price, total=total, id=id, symbol=symbol)

        # select stocks and convert to usd for index table
        stocks = db.execute("SELECT * FROM current WHERE id = :id", id=id)
        current_total = cash

        for i in range(len(stocks)):
            current_total = current_total + float(stocks[i]["total"])
            stocks[i]["price"] = usd(stocks[i]["price"])
            stocks[i]["total"] = usd(stocks[i]["total"])

        cash = usd(cash)
        current_total = usd(current_total)

         # Show index table
        return render_template("index.html", stocks=stocks, cash=cash, curent_total=current_total)

    else:
        cash = usd(users[0]["cash"])
        stocks = db.execute("SELECT * from current WHERE id = :id", id=session["user_id"])

        return render_template("sell.html", stocks=stocks, cash=cash)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)

if __name__ == "__main__":
    app.run()