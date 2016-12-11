# Miscellaneous Commands
---

* [Roll](#roll)
* [Flip](#flip)
* [Vote](#vote)

---

### Roll
#### Roll some dice and get the results.

Valid values for dice:

* XdY
* X
* dY

Where `X` is the number of dice and `Y` is the number of sides on each die.

`dice` in the examples can be any of the above.

Usage:

    !roll [dice list]
    !roll               : Roll 1d6
    !roll dice          : Roll the dice you specify
    !roll dice dice ... : Roll the dice you specify

---

### Flip
#### Flip some coins and get the results

There is 1/6001 chance of the coin landing on edge.

Usage:

    !flip [count]
    !flip   : Flip 1 coin
    !flip # : Flip # coins

---

### Choose
#### Choose one from a set of options.

Usage:

    !choose "a b c" def g h i   : select from options "a b c", "def", "g", "h", and "i"

---

### Vote
#### Allow users to vote on a topic.
##### Requires __the bot__ has the `Add Reactions` permission.

Within 30 seconds of starting it, the poll creator can add a :clockTIME: emoji to set
the poll time limit or :x: to cancel the poll.

Default time limit of 1 hour.
Allows a maximum of 10 options.
The person who starts the poll can end it early by adding the :x: emoji as a reaction.

Usage:

    ![vote|poll] <title> [options...]

    !poll What movie is best? : Creates poll with title "What movie is best?"
    Cinderella                : with options "Cinderella" and "Lion King"
    Lion King
