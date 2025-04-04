public class t6 {
public static void main(string[] args) {
java.util.scanner input = new java.util.scanner(system.in);
int[] num = new int[10];
for (int i = 0; i < 10; i++) {
system.out.print("read a number: ");
num[i] = input.nextint();
}
for (int i = 9; i >= 0; i--) {
system.out.println(num[i]);
}
}
}