#' greeting
#'
#' @param many_names Several names
#'
#' @return A greeting
#' @export
#'
#' @examples greetings(c("Alice", "Bob"))
greetings <- function(many_names){
  the_greetings <- stringr::str_c("Greetings ", many_names, ".")

  return(the_greetings)
}
