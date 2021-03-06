import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps


def apology(message, code=400):
    """Render message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/1.0/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# API Token: pk_58509b2580024502aa8fb7114d4672af
# https://cloud-sse.iexapis.com/stable/stock/{urllib.parse.quote_plus(AAPL)}/quote?token={pk_58509b2580024502aa8fb7114d4672af}

def lookup(symbol):
    """Look up quote for symbol."""

    # Contact API
    try:
        api_key = os.environ.get("API_KEY")
        symbol = urllib.parse.quote_plus(symbol)
        response = requests.get("https://cloud-sse.iexapis.com/stable/stock/"+symbol+"/quote?token=pk_58509b2580024502aa8fb7114d4672af")
        response.raise_for_status()
    except requests.RequestException:
        return None

    # Parse response
    try:
        quote = response.json()
        return {
            "name": quote["companyName"],
            "price": float(quote["latestPrice"]),
            "symbol": quote["symbol"]
        }
    except (KeyError, TypeError, ValueError):
        return None


def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


# export DATABASE_URL = postgres: // fjxwxmltbneqra: 14048b76e9edb786a84cf371825f7be1c61225e1cbf61bdfd1c2846a2f09e7fc@ec2-35-168-54-239.compute-1.amazonaws.com: 5432/d3m16sv2qdmmpr
# pgloader finance.db postgres: // fjxwxmltbneqra: 14048b76e9edb786a84cf371825f7be1c61225e1cbf61bdfd1c2846a2f09e7fc@ec2-35-168-54-239.compute-1.amazonaws.com: 5432/d3m16sv2qdmmpr?sslmode = require
