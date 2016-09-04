# Miscellaneous Commands
---

* [Roll](#roll)
* [Flip](#flip)
* [xkcd](#xkcd)

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

### xkcd
#### Get an xkcd comic.
Usage:

    !xkcd               : Get latest xkcd comic
    !xkcd #             : Get comic #
    !xkcd r/rand/random : Get a random comic
