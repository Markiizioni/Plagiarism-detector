import java.util.scanner;
public class t3 {
public static void main(string[] args) {
scanner input = new scanner(system.in);
system.out.print("enter weight in pounds: ");
double weight = input.nextdouble();
system.out.print("enter feet: ");
double feet = input.nextdouble();
system.out.print("enter inches: ");
double inches = input.nextdouble();
double height = feet * 12 + inches;
double bmi = weight * 0.45359237 / ((height * 0.0254) * (height * 0.0254));
system.out.println("bmi is " + bmi);
if (bmi < 18.5)
system.out.println("underweight");
else if (bmi < 25)
system.out.println("normal");
else if (bmi < 30)
system.out.println("overweight");
else
system.out.println("obese");
}
}