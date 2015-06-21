# liarsdice
liars dice, sometimes known as peruto

## Overview

Play liars dice, sometimes known as peruto, with friends or against the computer.

The computers algorithm is pretty simple but surprisingly effective.
75% of the time it will claim the highest expected value (from its point of view). 
25% of the time it will make a bs claim.

For instance, if the computer has:

1 6 2 3 6 

and you have 3 dice, it will: 

* claim 4 6's 75% of the time. ( it has 3, and if you have 6 dice then your expected amount of 6'1 is (2/6) * 3, since 1 or 6 will count as 6 ).

* Make a bs claim 25% of the time

This ridiculously simple algorithm is surprisingly effective.  Go ahead and see for yourself on http://liarsdice.joshyg.webfactional.com

## Rules of the Game

* You start out with 5 die.  1's are wild.  You roll.  
* You make a claim for the total amount of a particular number ( this includes the amounts from the rolls of all other players )
* The next player either makes a counter claim (for a higher die value _or_ the same value but a higher amount) or calls bullshit
* Every round ends with a bullshit call.  If the claim was bullshit, the claimer loses a die.  If it wasn't, the bullshitter loses a die
* All players roll again.  Repeat until only one player has die left.


The trick is that you have to keep track of the number of die remaining.  From here you can get the expected values of various outcomes.
For more info go [here](http://www.google.com) and type 'liars dice' in the search box.

## Why did I make this

I became obsessed with this game for like 2 months.  I wrote a script to see if it could beat my friends.  It did.  I briefly thought I was a genius.  I went home and made an app from the script.  The rest is history.


## Issues

* The python has two space indents, which was the style at the company I worked at at the time.  Shockingly they are still in business.
* The code could be more organized and the front end is pretty basic. One day...


## Disclaimer

The jchat app is not my code.  I pulled it from sourceforge when I first wrote this app.  To learn more enter jchat [here](http://www.google.com)
