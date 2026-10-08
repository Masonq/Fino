// Сборка для App Store (STORE_BUILD=1) — со «Войти с Apple»; сборка для SideStore — без: бесплатные аккаунты разработчика,
// которыми SideStore переподписывает приложение, эту возможность не дают, и установка бы не прошла.
const store = process.env.STORE_BUILD === '1'
module.exports = ({ config }) => ({
  ...config,
  ios: { ...config.ios, ...(store ? { usesAppleSignIn: true } : {}) },
  plugins: [...(config.plugins || []), ...(store ? ['expo-apple-authentication'] : [])],
  extra: { ...(config.extra || {}), storeBuild: store },
})
