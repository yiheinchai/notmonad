<h1 align="center">
  <br>
  <a href="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde"><img src="https://github.com/yiheinchai/notmonad/assets/76833604/afab9829-9fa8-4349-8f42-488ac21c1fde" alt="NotMonad" width="200"></a>
  <br>
  NotMonad
  <br>
</h1>

<h4 align="center">Helpful functions for pipeline style data transformation operations</h4>

<p align="center">
  <a href="https://gitter.im/yiheinchai/notmonad"><img src="https://badges.gitter.im/yiheinchai/notmonad.svg"></a>
  <a href="https://saythanks.io/to/chaiyihein@gmail.com">
      <img src="https://img.shields.io/badge/SayThanks.io-%E2%98%BC-1EAEDB.svg">
  </a>
  <a href="https://www.paypal.me/yiheinchai">
    <img src="https://img.shields.io/badge/$-donate-ff69b4.svg?maxAge=2592000&amp;style=flat">
  </a>
</p>

<p align="center">
  <a href="#use-cases">Use cases</a> •
  <a href="#api">API</a> •
  <a href="#motivations">Motivations</a> •
  <a href="#key-features">Key Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#download">Download</a> •
  <a href="#license">License</a>
</p>

![image](https://github.com/yiheinchai/notmonad/assets/76833604/7fd567e1-8292-47ca-b6a9-5ad284d3af75)

## Use cases

### Chaining operations together with a succinct syntax

The chain function enables the use of the chaining syntax:
`chain(<init_val>)(func, *params)(...)()`. The chain function is a shorthand for the Just monad, `monad(<init_val>, Just)(...)()`

```python
# With monad
val = np.array([[1,2,3],[1,2,3]])
chain(val)(np.transpose)(np.sum, axis=1)(np.mean)(lambda x: x/100)()
```

It is much more verbose without using monads:

```python
# Without
data = np.array([[1,2,3],[1,2,3]])
transposed_data = np.transpose(data)
summed_data = np.sum(transposed_data, axis=1)
mean_data = np.mean(summed_data)
perc_data = mean_data / 100
```

Clearly, the syntax becomes more more succinct using notmonad. Moreover, there is no need to come up with many intermediate variable names, preventing the pollution of the namespace.

### Clear error handling

With a pipeline of transformations, error handling means that you end up with the try-except/catch tower of terror or a pyramid of doom. While TanStack Query style [value, error] destructuring works, the Maybe Monad solves this problem much more elegantly and more concisely.

Railroad error handling with Maybe monad:

```python
val = np.array([[1,2,3],[1,2,3]])
monad(val, compose(maybe))(np.transpose)(np.sum, axis=1)(np.mean)(lambda x: x/0)(lambda x: x/100)() == None

```

Using try except results in the formation of tower of terror:

```python
try:
    data = np.array([[1,2,3],[1,2,3]])
except Exception as e:
    data = None

try:
    transposed_data = np.transpose(data)
except Exception as e:
    transposed_data = None

try:
    summed_data = np.sum(transposed_data, axis=1)
except Exception as e:
    summed_data = None

try:
    mean_data = np.mean(summed_data)
except Exception as e:
    mean_data = None

try:
    perc_data = mean_data / 100
except Exception as e:
    perc_data = None
```

### Clear debugging

One downside of using such one-liner chains is that if one function within the chain fails, the error message given does not specify which part of the chain that failed. To resolve this, we can use the Debug monad.

```python
monad(5, compose(debug, maybe))(add, 1)(lambda x: x / 0)(add, 3).keywords["_debug_trace"]

# OUTPUT:
# [
#     {
#         "func": "add",
#         "args": (5, 1),
#         "kwargs": {},
#         "value": 6,
#         "errors": "",
#         "repr": "add(5, 1) -> 6 []",
#     },
#     {
#         "func": "<lambda>",
#         "args": (6,),
#         "kwargs": {},
#         "value": None,
#         "errors": "division by zero",
#         "repr": "<lambda>(6,) -> None [division by zero]",
#     },
# ]
```

The debug trace shows exactly the functions that run at each step of the pipeline, the arguments that it was called with, the return values and the errors at each step.

### Monad Composition

Monads can be combined together using the `compose` function. This allows you to use multiple monads in a single data pipeline. For example:

```python
monad(5, compose(debug, log, shout maybe))(add, 1)(lambda x: x / 0)(add, 3)()

# OUTPUT:
# shout: I am shouting! add
# log: add
# debug: {
#         "func": "add",
#         "args": (5, 1),
#         "kwargs": {},
#         "value": 6,
#         "errors": "",
#         "repr": "add(5, 1) -> 6 []",
#     },

# shout: I am shouting! lambda
# log: lambda
# debug: {
#         "func": "<lambda>",
#         "args": (6,),
#         "kwargs": {},
#         "value": None,
#         "errors": "division by zero",
#         "repr": "<lambda>(6,) -> None [division by zero]",
#     }
```

With these composed monads, we run each of these monads at every step of the function pipeline, as a result, we will get a print of 'I am shouting' from the `shout` monad at every step. All this computation is done with the `compose` function. As the name suggests, `compose` function allows you to compose multiple monads and use them together. It takes in monads as an arguments and returns a new monad which is a composition of all the monads that was passed in.

We can see monads as the functions that in the intermediary step between two chained functions. There are two main types of monads:

1. Side-effect monads
2. Caller monads

Caller monads execute the function passed with the arguments provided and hence performs data transformation on the initial value. This can be indicated by the `@caller` decorator. In contrast, side-effect monads do not modify the underlying data, but instead log something, print something, do some intermediary computaton and pass that onto the next step in the pipeline.

Any composition of monad can only contains a single caller monad and any number of side-effect monads. This is because applying two caller monads will cause the data transformation function to be applied twice.

### Custom Monads

NotMonad also allows you to create your own custom monads to fit your use case. A monad can be used via the `compose` function. To create a monad that is compatible with the `compose` function, it must comply with the following format:

1. Args: `value, func, *args, **kwargs`
2. Returns: `value, func, *args, **kwargs`

If the function is called to modify the value returned, then it must have the `@caller` decorator.

### Loops and Memory storage

With the introduction of loops and memory storage, you can now write any python application entirely within NotMonad.

Loops can be written inside a lambda function or using the `loop` function. If else statements can be written inside a lambda function.

Now, with the memory storage API, you can post your current calculations into the function's memory, and hop onto a new set of calculations by `__mount` or `__get`, and hence continue calculations from there.

After getting both to the stage where you want to combine both calculations, you can use the `__call` method.
![image](https://github.com/yiheinchai/notmonad/assets/76833604/8090512b-f05b-492c-9c5f-0c1207303890)

## API

-   `chain(<val>)(<func>, *params)()`
    -   chain functions together, last parentheses returns the value
-   `monad(<val>, <Just | Maybe>)(<func>, *params)()`
    -   Just or Maybe (with cap first letter) are convenient monads that allows the use of monads without compose
-   `monad(<val>, compose(<monads>, <monads>,..))(<func>, *params)()`
    -   Compose monads together

## Motivations

In full admission, I do not study computer science or math, I do not understand monads or anything about category theory. Therefore, my use of the word 'monad' here is obviously very inaccurate and likely outright wrong.

This project spawned out of a need. I was performing some data analysis that requried lots of data augmentation and manipulation. It resembled a series of functions being applied to the same piece of data with that piece of data being passed from one function to the next.

In basic python, you can either do this by nesting one function into another, or you can create a bunch of intermediary variables names for each step. Nesting one function into another is a pain, because you start losing track deep within the parenthesis, and the function names read from right to left (which is inconvenient). Creating intermediary variables pollute the namespace, and when working with something like Jupyter notebooks, it often results in namespace pollution related bugs. Moreover, it is just a pain to think of variables names that you would not use again.

Chaining functions solves this problem, it prevents nesting, allows an easy to read left to right syntax, and pure use of parenthesis allows it to be very succinct, and also avoids namespace pollution.

Traditionally, monads are created by wrapping a value with a 'container'. Then that container has functions that allow another monad to act on it with a flatmap (to ensure only 1 layer of wrapping). However, the disadvantage is that the functions have to be responsible for the wrapping. That means that the monadic functions that you write cannot be used anywhere else. Moreover, you definitely cannot be lambda functions on the fly when you want to use chaining with traditional moands. Therefore, the approach was taken to separate the concerns of 'wrapping' and 'unwrapping' away, such that the only thing the functions need to do is to perform the data augmentation and nothing else.

In the context of this project, I like to think of monads as advanced decorators for every function in the pipeline that pass state from one function to the next.

Thinking of monads this way, allows you to realise that monads can literally be any function that does some intermediary computation. So here, we can do error handling, logging or even send an API request as part of the monad! Moreover, it then also makes sense to be able to do two intermediary computations between the functions. And this spawned monad composition, you can combine, mix and match any monads you have and it would work just as expected. Even more interestingly, we realise that this combination of monads can be done with a monad too. Therefore, there is a `mmonad` function that allows you to chain together monads to create a new combined monad. The monad's monad! It is interesting to think about the implications:

The chain of functions can be thought of as a series of data transformations...

```python
f(x): a -> b
g(x): b -> c

chain(x)(f)(g): a -> c
```

We can see that for function chaining to work, the type of the output of f must match up with the type of the output of g. And it is because of this reason, the order matters. The results of `chain(x)(f)(g)` is different from `chain(x)(g)(f)` it might even throw an error because the `c` and `a` are not matching types.

Now, we can see monads themselves as a series of intermediary data transformations, this is how the execution looks:

(function 1)(monad 1)(monad 2)(monad 3)(function 2)(monad 1)(monad 2)(...)...

The only difference is that monads carry the parameters that should be passed into the functions, and each monad conducts side effects based on the function parameters or even modify the function parameters themselves before it is being fed into the function.

As mentioned before, each monad takes in the params:`value, func, *args, **kwargs` and also returns the same params `value, func, *args, **kwargs`. The input and output types are the same. This means that:

```python
m(x): a -> a
c(x): a -> a

chain(x)(m)(c): a -> a
```

Therefore, because the input and output types of the monads are the same (monoidic) they can be chained in any order and it doesn't matter. It is also because that chaining monads is a monadic thing, we can use a meta-monad to generate chained monads (to modify the behaviour of how the monads are chained).

## Key Features

-   Just Monad
    -   Easy chaining of functions with parenthesis syntax
-   Maybe Monad
    -   Railway style error handling
-   Debug Monad
    -   Generate a debug trace to follow through pipeline execution
-   Log Monad
    -   Log the function execution history throughout the pipelien
-   Order Args Monad
    -   Enable ordering of arguments at each step of processing pipeline
-   Composable Monads
    -   Combine multiple monads together using a monad-monad or via the `compose` function.
-   Custom Monads
    -   Create your own custom monad that fits your use case

## Installation

To clone and run this application, you'll need [Git](https://git-scm.com) installed on your computer. From your command line:

```bash
# Clone this repository
$ git clone https://github.com/yiheinchai/notmonad

# Start python shell
$ python

# Import the repo
$ from notmonad import *
```

## Emailware

NotMonad is an [emailware](https://en.wiktionary.org/wiki/emailware). Meaning, if you liked using this app or it has helped you in any way, I'd like you send me an email at <chaiyihein@gmail.com> about anything you'd want to say about this software. I'd really appreciate it!

## Support

<a href="https://www.buymeacoffee.com/{id}" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/purple_img.png" alt="Buy Me A Coffee" style="height: 41px !important;width: 174px !important;box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;-webkit-box-shadow: 0px 3px 2px 0px rgba(190, 190, 190, 0.5) !important;" ></a>

<p>Or</p>

<a href="https://www.patreon.com/{id}">
	<img src="https://c5.patreon.com/external/logo/become_a_patron_button@2x.png" width="160">
</a>

## License

MIT

---

> Personal Website [yiheinchai.github.com](https://www.yiheinchai.github.com) &nbsp;&middot;&nbsp;

> GitHub [@yiheinchai](https://github.com/yiheinchai) &nbsp;&middot;&nbsp;

> Twitter [@chaiyihein](https://twitter.com/chaiyihein)
