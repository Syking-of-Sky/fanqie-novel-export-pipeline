package com.anjia.unidbgserver.service;

import org.junit.jupiter.api.Test;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;

/** Offline cryptographic regression tests; no network or APK/SO assets required. */
class FQEncryptServiceTest {

    @Test
    void aesCbcRoundTripUsesFixtureOnly() throws Exception {
        String key = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
        byte[] iv = new byte[16];
        for (int i = 0; i < iv.length; i++) {
            iv[i] = (byte) i;
        }
        byte[] plaintext = "fixture chapter payload".getBytes(StandardCharsets.UTF_8);
        FqCrypto crypto = new FqCrypto(key);
        byte[] ciphertext = crypto.encrypt(plaintext, iv);
        byte[] encoded = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, encoded, 0, iv.length);
        System.arraycopy(ciphertext, 0, encoded, iv.length, ciphertext.length);
        String base64 = java.util.Base64.getEncoder().encodeToString(encoded);

        assertArrayEquals(plaintext, crypto.decrypt(base64));
        assertEquals("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA", FqCrypto.byteArrayToHexString(
                FqCrypto.hexStringToByteArray(key)));
        assertEquals(plaintext.length, crypto.decrypt(base64).length);
        assertEquals(0, Arrays.compare(plaintext, crypto.decrypt(base64)));
    }
}
