import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Card,
  CardContent,
  CardActions,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Switch,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
  Snackbar,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  GitHub as GitHubIcon,
  Security as SecurityIcon,
  Build as BuildIcon,
  Sync as SyncIcon,
  Storage as StorageIcon,
  ExpandMore as ExpandMoreIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Helmet } from 'react-helmet-async';

import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';

const Settings: React.FC = () => {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  
  const [configDialogOpen, setConfigDialogOpen] = useState(false);
  const [buildDialogOpen, setBuildDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });

  // Queries
  const { data: configStatus, isLoading: configLoading, refetch: refetchConfig } = useQuery({
    queryKey: ['config-status'],
    queryFn: apiService.getConfigStatus,
  });

  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['health'],
    queryFn: apiService.getHealth,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Mutations
  const generateConfigMutation = useMutation({
    mutationFn: apiService.generateUnifiedConfig,
    onSuccess: () => {
      setBuildDialogOpen(false);
      setSnackbar({
        open: true,
        message: 'Unified configuration generated successfully!',
        severity: 'success',
      });
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message: error.detail || 'Failed to generate configuration',
        severity: 'error',
      });
    },
  });

  // Helper functions
  const getStatusIcon = (status: boolean) => {
    return status ? <CheckIcon color="success" /> : <ErrorIcon color="error" />;
  };

  const getStatusChip = (status: boolean, label?: string) => {
    return (
      <Chip
        label={label || (status ? 'OK' : 'Issue')}
        color={status ? 'success' : 'error'}
        size="small"
        icon={getStatusIcon(status)}
      />
    );
  };

  const handleGenerateConfig = () => {
    generateConfigMutation.mutate();
  };

  const handleRefreshStatus = () => {
    refetchConfig();
    queryClient.invalidateQueries({ queryKey: ['health'] });
  };

  return (
    <>
      <Helmet>
        <title>Settings - FactFiber Documentation</title>
        <meta name="description" content="System settings and configuration for FactFiber documentation" />
      </Helmet>

      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            System Settings
          </Typography>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={handleRefreshStatus}
            disabled={configLoading || healthLoading}
          >
            Refresh Status
          </Button>
        </Box>

        {/* System Status Overview */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SettingsIcon />
            System Status
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    {getStatusIcon(configStatus?.github_configured || false)}
                  </ListItemIcon>
                  <ListItemText
                    primary="GitHub Integration"
                    secondary="API access and repository management"
                  />
                  {getStatusChip(configStatus?.github_configured || false)}
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    {getStatusIcon(configStatus?.oauth2_proxy_configured || false)}
                  </ListItemIcon>
                  <ListItemText
                    primary="OAuth2-Proxy"
                    secondary="Authentication and authorization"
                  />
                  {getStatusChip(configStatus?.oauth2_proxy_configured || false)}
                </ListItem>
              </List>
            </Grid>
            <Grid item xs={12} md={6}>
              <List>
                <ListItem>
                  <ListItemIcon>
                    {getStatusIcon(configStatus?.mkdocs_configured || false)}
                  </ListItemIcon>
                  <ListItemText
                    primary="MkDocs Configuration"
                    secondary="Documentation site generation"
                  />
                  {getStatusChip(configStatus?.mkdocs_configured || false)}
                </ListItem>
                <ListItem>
                  <ListItemIcon>
                    {getStatusIcon(configStatus?.temp_dir_writable || false)}
                  </ListItemIcon>
                  <ListItemText
                    primary="Storage Access"
                    secondary="Temporary file directory permissions"
                  />
                  {getStatusChip(configStatus?.temp_dir_writable || false)}
                </ListItem>
              </List>
            </Grid>
          </Grid>

          {health && (
            <Box sx={{ mt: 2 }}>
              <Alert severity="success">
                System is healthy. Last check: {new Date(health.timestamp).toLocaleString()}
              </Alert>
            </Box>
          )}
        </Paper>

        {/* Configuration Sections */}
        <Grid container spacing={3}>
          {/* GitHub Configuration */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <GitHubIcon />
                  GitHub Configuration
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Configure GitHub API access for repository discovery and management.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="API Access"
                      secondary={configStatus?.github_configured ? 'Connected' : 'Not configured'}
                    />
                    {getStatusChip(configStatus?.github_configured || false)}
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Enrolled Repositories"
                      secondary={`${configStatus?.enrolled_repositories || 0} repositories`}
                    />
                  </ListItem>
                </List>
              </CardContent>
              <CardActions>
                <Button size="small" disabled>
                  Configure GitHub
                </Button>
                <Button size="small" href="/docs/dev/getting-started" target="_blank">
                  Documentation
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* Authentication Configuration */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <SecurityIcon />
                  Authentication
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  OAuth2-Proxy integration for secure authentication.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="OAuth2-Proxy"
                      secondary={configStatus?.oauth2_proxy_configured ? 'Configured' : 'Not configured'}
                    />
                    {getStatusChip(configStatus?.oauth2_proxy_configured || false)}
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Current User"
                      secondary={user?.username || 'Unknown'}
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="User Teams"
                      secondary={user?.teams?.join(', ') || 'None'}
                    />
                  </ListItem>
                </List>
              </CardContent>
              <CardActions>
                <Button size="small" disabled>
                  Configure OAuth
                </Button>
                <Button size="small" href="/docs/oauth2-proxy-setup" target="_blank">
                  Setup Guide
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* Build Configuration */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <BuildIcon />
                  Documentation Build
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Generate unified MkDocs configuration and build documentation.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="MkDocs Config"
                      secondary={configStatus?.mkdocs_configured ? 'Valid' : 'Needs attention'}
                    />
                    {getStatusChip(configStatus?.mkdocs_configured || false)}
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Unified Config"
                      secondary="Generate configuration for all repositories"
                    />
                  </ListItem>
                </List>
              </CardContent>
              <CardActions>
                <Button
                  size="small"
                  variant="contained"
                  onClick={() => setBuildDialogOpen(true)}
                  disabled={generateConfigMutation.isPending}
                >
                  Generate Config
                </Button>
                <Button size="small" href="/docs/dev/devspace-guide" target="_blank">
                  Build Guide
                </Button>
              </CardActions>
            </Card>
          </Grid>

          {/* Storage Configuration */}
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                  <StorageIcon />
                  Storage & Sync
                </Typography>
                <Typography variant="body2" color="text.secondary" paragraph>
                  Temporary storage and synchronization settings.
                </Typography>
                <List dense>
                  <ListItem>
                    <ListItemText
                      primary="Temp Directory"
                      secondary={configStatus?.temp_dir_writable ? 'Writable' : 'Permission denied'}
                    />
                    {getStatusChip(configStatus?.temp_dir_writable || false)}
                  </ListItem>
                  <ListItem>
                    <ListItemText
                      primary="Auto Sync"
                      secondary="Webhook-based synchronization"
                    />
                    <Chip label="Enabled" color="success" size="small" />
                  </ListItem>
                </List>
              </CardContent>
              <CardActions>
                <Button size="small" disabled>
                  Configure Storage
                </Button>
                <Button size="small" href="/webhooks/sync/status" target="_blank">
                  View Sync Status
                </Button>
              </CardActions>
            </Card>
          </Grid>
        </Grid>

        {/* Advanced Settings */}
        <Box sx={{ mt: 4 }}>
          <Accordion>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="h6">Advanced Settings</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>
                    System Information
                  </Typography>
                  <List dense>
                    <ListItem>
                      <ListItemText
                        primary="API Base URL"
                        secondary={process.env.REACT_APP_API_URL || '/api'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Environment"
                        secondary={process.env.NODE_ENV || 'development'}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Build Version"
                        secondary={process.env.REACT_APP_VERSION || '0.1.0'}
                      />
                    </ListItem>
                  </List>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle1" gutterBottom>
                    Useful Links
                  </Typography>
                  <List dense>
                    <ListItem>
                      <Button href="/docs/" target="_blank" size="small">
                        Documentation Home
                      </Button>
                    </ListItem>
                    <ListItem>
                      <Button href="/docs/dev/getting-started" target="_blank" size="small">
                        Developer Guide
                      </Button>
                    </ListItem>
                    <ListItem>
                      <Button href="/docs/dev/devspace-guide" target="_blank" size="small">
                        DevSpace Guide
                      </Button>
                    </ListItem>
                    <ListItem>
                      <Button href="/health/" target="_blank" size="small">
                        API Health Check
                      </Button>
                    </ListItem>
                  </List>
                </Grid>
              </Grid>
            </AccordionDetails>
          </Accordion>
        </Box>

        {/* Build Configuration Dialog */}
        <Dialog open={buildDialogOpen} onClose={() => setBuildDialogOpen(false)} maxWidth="sm" fullWidth>
          <DialogTitle>Generate Unified Configuration</DialogTitle>
          <DialogContent>
            <Typography paragraph>
              This will generate a unified MkDocs configuration file that includes all enrolled repositories
              and their navigation structures.
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
              The configuration will be generated based on currently enrolled repositories and their sections.
              Make sure all repositories are properly enrolled before generating.
            </Alert>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setBuildDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleGenerateConfig}
              variant="contained"
              disabled={generateConfigMutation.isPending}
              startIcon={generateConfigMutation.isPending ? <CircularProgress size={20} /> : <BuildIcon />}
            >
              {generateConfigMutation.isPending ? 'Generating...' : 'Generate'}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Snackbar for notifications */}
        <Snackbar
          open={snackbar.open}
          autoHideDuration={6000}
          onClose={() => setSnackbar({ ...snackbar, open: false })}
        >
          <Alert
            onClose={() => setSnackbar({ ...snackbar, open: false })}
            severity={snackbar.severity}
            sx={{ width: '100%' }}
          >
            {snackbar.message}
          </Alert>
        </Snackbar>
      </Box>
    </>
  );
};

export default Settings;