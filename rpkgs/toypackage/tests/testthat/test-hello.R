test_that("hello works", {
  test_name <- "Alice"
  test_message <- paste0("Hello ", test_name, "!")

  expect_identical(test_message, hello(test_name))
})
