# https://www.prestevez.com/post/r-package-tutorial/#what-are-packages

# install.packages(c("devtools", "roxygen2", "testthat", "knitr"))

devtools::has_devel()
#> Your system is ready to build packages!

# Load devtools and friends
library(devtools)

# Create the file structure
# create_package("~/projects/packages/toypackage") ## write the path to your WD

use_git()


use_r("hello")
load_all()
hello("Patricio")

check()

use_mit_license("Fernando Marcon Passos")
document()

check()

install()

usethis::use_testthat()
use_test("hello")

test()

use_package("stringr")
use_r("greetings")
document()
load_all()
greetings(c("Alice", "Bob"))


# Use this command if you have SSH keys associated with Github
use_github(protocol = "ssh")

# Use this command if you don't
use_github()


use_readme_rmd()
build_readme()
# Commit and push the changes you made and visit your Github repository, it should look like this: prestevez/toypackage.
# This package can now be installed from anywhere in the world using this command:
library(devtools)
install_github("prestevez/toypackage")
