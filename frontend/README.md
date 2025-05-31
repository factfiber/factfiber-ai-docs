# FactFiber Documentation Frontend

Modern React TypeScript frontend for the FactFiber Documentation Infrastructure system.

## Features

- **Modern React 18** with TypeScript and functional components
- **Material-UI v5** with responsive design and dark mode support
- **Authentication Integration** with GitHub OAuth2-Proxy and JWT tokens
- **Repository Management** - Enroll, unenroll, and manage documentation repositories
- **Advanced Search** - Full-text search with filtering and faceted search
- **Real-time Updates** - Live sync status and webhook integration
- **Progressive Web App** - Service worker and offline capabilities
- **Mobile Responsive** - Optimized for all device sizes
- **Developer Experience** - Hot reloading, TypeScript, ESLint, Prettier

## Quick Start

### Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm start

# Open http://localhost:3000
```

### Production Build

```bash
# Build for production
npm run build

# Serve production build
npm run serve
```

### Docker Development

```bash
# Build development image
docker build --target development -t ff-docs-frontend:dev .

# Run development container
docker run -p 3000:3000 -v $(pwd):/app ff-docs-frontend:dev
```

### DevSpace Integration

```bash
# Start full development environment
devspace dev

# Frontend will be available at http://localhost:3000
```

## Project Structure

```text
frontend/
├── public/                 # Static assets
│   ├── index.html         # HTML template
│   ├── manifest.json      # PWA manifest
│   └── sw.js              # Service worker
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── Layout.tsx     # Main layout with navigation
│   │   └── LoadingScreen.tsx
│   ├── pages/             # Page components
│   │   ├── Dashboard.tsx  # Main dashboard
│   │   ├── Repositories.tsx # Repository management
│   │   ├── Search.tsx     # Advanced search interface
│   │   ├── Settings.tsx   # System settings
│   │   └── Login.tsx      # Authentication
│   ├── hooks/             # Custom React hooks
│   │   └── useAuth.tsx    # Authentication context
│   ├── services/          # API and external services
│   │   └── api.ts         # FastAPI backend integration
│   ├── types/             # TypeScript type definitions
│   │   ├── api.ts         # API response types
│   │   └── index.ts       # Common types
│   ├── utils/             # Utility functions
│   ├── App.tsx            # Main application component
│   └── index.tsx          # Application entry point
├── Dockerfile             # Multi-stage Docker build
├── nginx.conf             # Production nginx configuration
└── package.json           # Dependencies and scripts
```

## Available Scripts

- `npm start` - Start development server with hot reloading
- `npm run build` - Build production bundle
- `npm test` - Run test suite
- `npm run lint` - Run ESLint
- `npm run lint:fix` - Fix ESLint issues
- `npm run format` - Format code with Prettier
- `npm run type-check` - Run TypeScript compiler check

## Configuration

### Environment Variables

Create a `.env.local` file based on `.env.example`:

```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_VERSION=0.1.0

# OAuth2-Proxy Configuration
REACT_APP_OAUTH2_PROXY_URL=http://localhost:4180

# Feature Flags
REACT_APP_ENABLE_PWA=true
REACT_APP_ENABLE_ANALYTICS=false
```

### API Integration

The frontend communicates with the FastAPI backend through:

- **Authentication endpoints** - `/auth/login`, `/auth/status`, `/auth/me`
- **Repository management** - `/repos/`, `/repos/discover`, `/repos/enroll`
- **Search functionality** - `/docs/search`
- **Webhook status** - `/webhooks/sync/status`

### Authentication Flow

1. **OAuth2-Proxy** (Recommended)
   - Redirects to GitHub OAuth
   - Sets authentication headers
   - Automatic token management

2. **Personal Access Token**
   - Manual token entry
   - Stored in localStorage
   - JWT authentication

## Development

### Code Style

- **TypeScript** - Full type safety with strict mode
- **ESLint** - Code quality and consistency
- **Prettier** - Code formatting
- **Material-UI** - Component library and design system

### State Management

- **React Context** - Authentication state
- **TanStack Query** - Server state and caching
- **React Hook Form** - Form state and validation

### Testing

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run tests in watch mode
npm test -- --watch
```

### Performance

- **Code splitting** - Automatic route-based splitting
- **Bundle optimization** - Tree shaking and minification
- **Service worker** - Asset caching and offline support
- **Image optimization** - Responsive images and lazy loading

## Deployment

### Production Deployment

```bash
# Create optimized production build
npm run build

# Serve with nginx
docker build --target production -t ff-docs-frontend:prod .
docker run -p 80:80 ff-docs-frontend:prod
```

### Kubernetes Deployment

The frontend is integrated with the DevSpace configuration for Kubernetes deployment:

```yaml
# DevSpace will build and deploy the frontend
images:
  frontend:
    image: ghcr.io/factfiber/ff-docs-frontend
    dockerfile: ./frontend/Dockerfile
```

### Environment-Specific Configuration

- **Development** - Hot reloading, source maps, debug tools
- **Staging** - Production build with staging API endpoints
- **Production** - Optimized build with CDN and compression

## Browser Support

- **Modern browsers** - Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile browsers** - iOS Safari 14+, Chrome Mobile 90+
- **Progressive Enhancement** - Graceful degradation for older browsers

## Accessibility

- **WCAG 2.1 AA** compliance
- **Keyboard navigation** - Full keyboard accessibility
- **Screen readers** - ARIA labels and semantic HTML
- **High contrast** - Support for high contrast mode
- **Reduced motion** - Respects prefers-reduced-motion

## PWA Features

- **Service Worker** - Asset caching and offline support
- **App Manifest** - Install prompt and app-like experience
- **Responsive Design** - Mobile-first responsive layout
- **Performance** - Fast loading and smooth interactions

## Troubleshooting

### Common Issues

1. **API Connection Failed**

   ```bash
   # Check backend is running
   curl http://localhost:8000/health/

   # Verify CORS configuration
   ```

2. **Authentication Issues**

   ```bash
   # Clear localStorage
   localStorage.removeItem('ff_docs_token')

   # Check OAuth2-Proxy configuration
   ```

3. **Build Failures**

   ```bash
   # Clear cache and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

### Debug Mode

```bash
# Start with debug information
REACT_APP_DEBUG=true npm start

# Enable verbose logging
REACT_APP_LOG_LEVEL=debug npm start
```

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for all new code
3. Write tests for new components and features
4. Update documentation for new features
5. Ensure mobile responsiveness
6. Test with screen readers and keyboard navigation

## Performance Monitoring

The frontend includes performance monitoring:

- **Web Vitals** - Core Web Vitals measurement
- **Bundle Analysis** - Bundle size monitoring
- **Error Tracking** - Runtime error reporting
- **User Analytics** - Usage patterns and performance

For detailed performance analysis:

```bash
# Analyze bundle size
npm run build
npx webpack-bundle-analyzer build/static/js/*.js
```
