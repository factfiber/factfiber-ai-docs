import React, { useState } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  Alert,
  CircularProgress,
  Container,
  Stack,
  Divider,
} from '@mui/material';
import { GitHub, VpnKey } from '@mui/icons-material';
import { useAuth } from '@/hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

const Login: React.FC = () => {
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleTokenLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token.trim()) {
      setError('Please enter a valid token');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(token);
      navigate('/');
    } catch (err: any) {
      setError(err.detail || 'Login failed. Please check your token.');
    } finally {
      setLoading(false);
    }
  };

  const handleOAuth2ProxyLogin = () => {
    // Redirect to OAuth2-Proxy authentication
    window.location.href = '/oauth2/start?rd=' + encodeURIComponent(window.location.origin);
  };

  return (
    <>
      <Helmet>
        <title>Login - FactFiber Documentation</title>
        <meta name="description" content="Login to access FactFiber documentation system" />
      </Helmet>
      
      <Container maxWidth="sm">
        <Box
          sx={{
            marginTop: 8,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            minHeight: '100vh',
            justifyContent: 'center',
          }}
        >
          <Paper elevation={3} sx={{ padding: 4, width: '100%' }}>
            <Box sx={{ textAlign: 'center', mb: 4 }}>
              <Typography component="h1" variant="h4" gutterBottom>
                FactFiber Docs
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Centralized Documentation System
              </Typography>
            </Box>

            <Stack spacing={3}>
              {/* OAuth2-Proxy Login */}
              <Box>
                <Button
                  fullWidth
                  variant="contained"
                  size="large"
                  startIcon={<GitHub />}
                  onClick={handleOAuth2ProxyLogin}
                  sx={{ py: 1.5 }}
                >
                  Sign in with GitHub
                </Button>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
                  Recommended for most users
                </Typography>
              </Box>

              <Divider>
                <Typography variant="body2" color="text.secondary">
                  OR
                </Typography>
              </Divider>

              {/* Token Login */}
              <Box component="form" onSubmit={handleTokenLogin}>
                <Typography variant="h6" gutterBottom>
                  Developer Access
                </Typography>
                <TextField
                  fullWidth
                  label="GitHub Personal Access Token"
                  type="password"
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  margin="normal"
                  helperText="Enter your GitHub personal access token for API access"
                />
                
                {error && (
                  <Alert severity="error" sx={{ mt: 2 }}>
                    {error}
                  </Alert>
                )}

                <Button
                  type="submit"
                  fullWidth
                  variant="outlined"
                  disabled={loading || !token.trim()}
                  startIcon={loading ? <CircularProgress size={20} /> : <VpnKey />}
                  sx={{ mt: 2 }}
                >
                  {loading ? 'Signing in...' : 'Sign in with Token'}
                </Button>
              </Box>

              <Box sx={{ mt: 3 }}>
                <Typography variant="body2" color="text.secondary" align="center">
                  Need help? Contact your system administrator or check the{' '}
                  <a href="/docs/dev/getting-started" target="_blank" rel="noopener noreferrer">
                    documentation
                  </a>
                </Typography>
              </Box>
            </Stack>
          </Paper>
        </Box>
      </Container>
    </>
  );
};

export default Login;