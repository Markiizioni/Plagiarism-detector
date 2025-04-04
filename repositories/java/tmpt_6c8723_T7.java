import java.util.scanner;
public class t7 {
public static void main(string[] args) {
scanner input = new scanner(system.in);
system.out.print("enter a 4 by 4 matrix row by row: ");
double[][] m = new double[4][4];
for (int i = 0; i < 4; i++)
for (int j = 0; j < 4; j++)
m[i][j] = input.nextdouble();
system.out.print("sum of the elements in the major diagonal is " + summajordiagonal(m));
}
public static double summajordiagonal(double[][] m) {
double sum = 0;
for (int i = 0; i < m.length; i++)
sum += m[i][i];
return sum;
}
}