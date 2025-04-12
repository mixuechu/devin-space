const { createProxyMiddleware } = require('http-proxy-middleware');

module.exports = function(app) {
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'https://mcp-server-app-tunnel-fbdgpvrm.devinapps.com',
      changeOrigin: true,
      secure: false,
      pathRewrite: {
        '^/api': '/api',
      },
      onProxyReq: function(proxyReq) {
        proxyReq.setHeader('Authorization', 'Basic ' + Buffer.from('user:5aa57996663a206a9f5b8f185191124e').toString('base64'));
      }
    })
  );
};
