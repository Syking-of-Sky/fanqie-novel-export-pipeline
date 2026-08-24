package com.anjia.unidbgserver.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * FQ API 配置属性
 * 用于管理FQ API的设备参数和请求配置
 */
@Data
@Component
@ConfigurationProperties(prefix = "fq.api")
public class FQApiProperties {

    /** Enable live upstream calls. Keep false until deployment credentials are configured. */
    private boolean enabled = false;

    /**
     * API基础URL
     */
    private String baseUrl = "https://example.invalid";

    /**
     * 默认User-Agent
     */
    private String userAgent = "";

    /**
     * Cookie配置
     */
    private String cookie = "";

    /** Deployment-only AES registration key. Never commit a real value. */
    private String registrationKey = "";

    /**
     * 设备参数配置
     */
    private Device device = new Device();

    @Data
    public static class Device {
        /**
         * 设备唯一标识符
         */
        private String cdid = "";

        /**
         * 安装ID
         */
        private String installId = "";

        /**
         * 设备ID
         */
        private String deviceId = "";

        /**
         * 应用ID
         */
        private String aid = "1967";

        /**
         * 版本代码
         */
        private String versionCode = "68132";

        /**
         * 版本名称
         */
        private String versionName = "6.8.1.32";

        /**
         * 更新版本代码
         */
        private String updateVersionCode = "68132";

        /**
         * 设备类型
         */
        private String deviceType = "";

        /**
         * 设备品牌
         */
        private String deviceBrand = "";

        /**
         * ROM版本
         */
        private String romVersion = "";

        /**
         * 分辨率
         */
        private String resolution = "";

        /**
         * DPI
         */
        private String dpi = "";

        /**
         * 主机ABI
         */
        private String hostAbi = "";
    }
}
