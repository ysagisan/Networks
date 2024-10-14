package org.example;

import java.io.IOException;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.ReentrantLock;

public class MulticastListener {
    private final String multicastGroup;
    private final int port;
    private final boolean isIPv6;
    private final Map<String, Long> aliveCopies = new ConcurrentHashMap<>();
    private final ReentrantLock lock = new ReentrantLock();
    private static final int MULTICAST_TTL = 2;
    private static final int HEARTBEAT_INTERVAL = 2000;
    private static final int TIMEOUT = 5000;

    public MulticastListener(String multicastGroup, int port) {
        this.multicastGroup = multicastGroup;
        this.port = port;
        this.isIPv6 = multicastGroup.contains(":");
    }

    public void start() {
        // Поток для прослушивания мультикаст сообщений
        Thread listenerThread = new Thread(this::listenMulticast);
        listenerThread.setDaemon(true);
        listenerThread.start();

        // Поток для отправки мультикаст сообщений
        Thread senderThread = new Thread(this::sendMulticast);
        senderThread.setDaemon(true);
        senderThread.start();

        // Основной цикл для проверки активных копий
        while (true) {
            try {
                Thread.sleep(1000);
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            checkAliveCopies();
        }
    }

    private void listenMulticast() {
        try (MulticastSocket socket = isIPv6 ? new MulticastSocket(port) : new MulticastSocket(port)) {
            InetAddress group = InetAddress.getByName(multicastGroup);

            // Присоединяемся к мультикаст группе
            socket.joinGroup(new InetSocketAddress(group, port), NetworkInterface.getByInetAddress(group));
            System.out.println("Listening for multicast messages on " + multicastGroup + ":" + port);

            byte[] buffer = new byte[1024];
            while (true) {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                socket.receive(packet);

                String message = new String(packet.getData(), 0, packet.getLength(), StandardCharsets.UTF_8);
                if ("ALIVE".equals(message)) {
                    String senderAddress = packet.getAddress().getHostAddress();
                    lock.lock();
                    try {
                        aliveCopies.put(senderAddress, Instant.now().toEpochMilli());
                    } finally {
                        lock.unlock();
                    }
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    private void sendMulticast() {
        try (MulticastSocket socket = new MulticastSocket()) {
            InetAddress group = InetAddress.getByName(multicastGroup);

            // Устанавливаем TTL для мультикаст пакетов
            socket.setTimeToLive(MULTICAST_TTL);

            byte[] message = "ALIVE".getBytes(StandardCharsets.UTF_8);
            DatagramPacket packet = new DatagramPacket(message, message.length, group, port);

            while (true) {
                socket.send(packet); // Отправляем пакет
                Thread.sleep(HEARTBEAT_INTERVAL); // Ждем интервал перед отправкой следующего сообщения
            }
        } catch (IOException | InterruptedException e) {
            e.printStackTrace();
        }
    }


    private void checkAliveCopies() {
        long currentTime = Instant.now().toEpochMilli();
        lock.lock();
        try {
            aliveCopies.entrySet().removeIf(entry -> currentTime - entry.getValue() > TIMEOUT);
            if (!aliveCopies.isEmpty()) {
                System.out.println("Active copies: " + new ArrayList<>(aliveCopies.keySet()));
            }
        } finally {
            lock.unlock();
        }
    }
}
