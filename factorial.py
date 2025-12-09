def factorial(n):
    if n==1:
        return n
    else:
        return n*factorial(n-1)
    

num= int(input("Enter a number to find its factorial: "))


if num<0:
    print("Factorial is not defined for negative numbers.")

elif num==0:
    print("Factorial of 0 is 1.")
else:
    print("The Factorial of", num, "is", factorial(num))