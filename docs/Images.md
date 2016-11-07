# Image Commands
---

* [xkcd](#xkcd)
* [Cat](#cat)
* [- Facts](#facts)
* [- Ratings](#ratings)
* [- Rerate](#rerate)
* [- Faves](#faves)

---

### xkcd
#### Get an xkcd comic.
Usage:

    !xkcd               : Get latest xkcd comic
    !xkcd #             : Get comic #
    !xkcd r/rand/random : Get a random comic

---

## Cat
#### Get a random cat image and fact.
Available categories:

* hats
* space
* funny
* sunglasses
* boxes
* caturday
* ties
* dream
* sinks
* clothes

Usage:

    !cat [category]     : Get random image, optionally with a category.

After the bot replies with an image, for the next 30 seconds, anyone can rate the image, favorite it, or report it.

To rate the image, reply "X/10" where X is any number 1-10. Any number less than 1 will be changed to 1 and any number greater than 10 will be changed to 10.
To favorite the image, reply "fave", "favorite", or "favourite".
To report the image, reply "report" or "report and your reason here".

---

### Facts
#### Get cat facts.
This can be called with either `!cat fact` or `!cat facts`

[count] can be any number from 1 to 20. Default: 1

Usage:

    !cat facts [count]

    !cat facts          : Get 1 cat fact.
    !cat facts 5        : Get 5 cat facts.

---

### Ratings
#### Get a list of images you've rated.
Note this is in a code block to avoid image spam.

Usage:

    !cat ratings

---

### Rerate
#### Re-rate an image you've previously rated.
Usage:

    !cat rerate <image_id> <new_score>

    !cat rerate bC24 7
    !cat rerate bC24 7/10

---

### Faves
#### See all the images you've favorited.
This can be called with `!cat faves`, `!cat favorites`, or `!cat favourites`.

Usage:

    !cat faves [to_remove]

    !cat faves              : List favorited images.
    !cat faves bC24         : Unfavorite image "bC24"
