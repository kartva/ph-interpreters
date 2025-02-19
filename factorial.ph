fn factorial(n) {
    if n {
        return n * factorial(n - 1);
    } else {
        return 1;
    };
}
fn main() {
    print(factorial(5));
    return 0;
}
