package com.anjia.unidbgserver.dto;

import com.anjia.unidbgserver.service.FqCrypto;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

/**
 * FQNovel 注册密钥载荷
 * 对应 Rust 中的 FqRegisterKeyPayload 结构
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class FqRegisterKeyPayload {

    /**
     * 密钥内容 (加密后的)
     */
    @JsonProperty("content")
    private String content;

    /**
     * 密钥版本
     */
    @JsonProperty("keyver")
    private long keyver;

    /**
     * 根据变量创建注册密钥载荷
     *
     * @param var FQ变量
     */
    public FqRegisterKeyPayload(FqVariable var, String registrationKey) throws Exception {
        FqCrypto crypto = new FqCrypto(requireRegistrationKey(registrationKey));
        this.content = crypto.newRegisterKeyContent(var.getServerDeviceId(), "0");
        this.keyver = 1;
    }

    private static String requireRegistrationKey(String value) {
        if (value == null || value.trim().isEmpty()) {
            throw new IllegalStateException("fq.api.registration-key is not configured");
        }
        return value.trim();
    }

    /**
     * 获取解密后的真实密钥 (前16字节)
     * 使用新的解密算法，遵循 Python 中的 decrypt_registerkey 模式
     *
     * @return 十六进制密钥字符串 (前16字节)
     */
    @JsonIgnore
    public String getDecryptedKey(String registrationKey) throws Exception {
        return FqCrypto.getRealKey(this.content, registrationKey);
    }
}
