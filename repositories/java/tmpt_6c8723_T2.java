import java.util.scanner;
public class t2 {
public static void main(string[] args) {
scanner input = new scanner(system.in);
system.out.print("enter the radius and length of a cylinder: ");
double radius = input.nextdouble();
double length = input.nextdouble();
double area = radius * radius * 3.14159;
double volume = area * length;
system.out.println("the area is " + area);
system.out.println("the volume of the cylinder is " + volume);
}
}