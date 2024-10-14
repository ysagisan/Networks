package org.example;

public class Main {
    public static void main(String[] args) {
        if (args.length != 1) {
            System.out.println("Usage: java MulticastListener <multicast_group>");
            System.exit(1);
        }

        String multicastGroup = args[0];
        MulticastListener listener = new MulticastListener(multicastGroup, 50000);
        listener.start();
    }
}
