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

### Vote
#### Allow users to vote on a topic.
##### Requires __the bot__ has the `Add Reactions` permission.

Built-in time limit of 1 hour.
Allows a maximum of 10 options.
The person who starts the poll can end it early by adding the poop emoji as a reaction.

Any parameter with spaces needs to be wrapped in double quotes (").
`Lion King` is two options, `"Lion King"` is one option.

Usage:

    ![vote|poll] <title> [options...]

    !poll "A, B, or C?" A B C       : Creates poll with title "A, B, or C?" and options "A", "B", and "C"
    !poll "What movie is best?" Cinderella "Lion King" : Creates poll with title "What movie is best?"
                                                         with options "Cinderella" and "Lion King"
