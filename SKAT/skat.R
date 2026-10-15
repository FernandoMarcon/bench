#!/usr/bin/env r

library(SKAT)
data(SKAT.example)
names(SKAT.example)

attach(SKAT.example)

# --- Continuous trait
obj <- SKAT_Null_Model(y.c ~ X, out_type="C")
out.c <- SKAT(Z, obj)
out.c$p.value

# --- Dichotomous trait
obj <- SKAT_Null_Model(y.b ~ X, out_type="D")
out.bout.b <- SKAT(Z, obj)
out.b$p.value

# --- With MA adjustment for sample size < 2000
IDX <- c(1:100,1001:1100)
obj.s <- SKAT_Null_Model(y.b[IDX] ~ X[IDX,], out_type="D")
out.ma <- SKAT(Z[IDX,], obj.s, kernel = "linear.weighted")
out.ma$p.value
out.ma$results

# --- Binary Robust approach
out <- SKATBinary_Robust(Z[IDX,], obj.s, kernel = "linear.weighted")
out$p.value
