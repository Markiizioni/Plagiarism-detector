public class t5 {
public static void main(string[] args) {
system.out.print("enter an integer: ");
java.util.scanner input = new java.util.scanner(system.in);
int number = input.nextint();
reverse(number);
}
public static void reverse(int number) {
while (number != 0) {
int remainder = number % 10;
system.out.print(remainder);
number = number / 10;
}
system.out.println();
}
}