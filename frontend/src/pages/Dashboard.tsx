import React from 'react';
import {
  Box,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Chip,
  LinearProgress,
  Alert,
  Button,
  Skeleton,
} from '@mui/material';
import {
  LibraryBooks as LibraryBooksIcon,
  Search as SearchIcon,
  Sync as SyncIcon,
  TrendingUp as TrendingUpIcon,
  Schedule as ScheduleIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Settings as SettingsIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

import { apiService } from '@/services/api';
import { useAuth } from '@/hooks/useAuth';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  // Queries
  const { data: dashboard, isLoading: dashboardLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: apiService.getDashboard,
  });

  const { data: configStatus, isLoading: configLoading } = useQuery({
    queryKey: ['config-status'],
    queryFn: apiService.getConfigStatus,
  });

  const { data: syncStatuses = {}, isLoading: syncLoading } = useQuery({
    queryKey: ['sync-statuses'],
    queryFn: () => apiService.getSyncStatus() as Promise<Record<string, any>>,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Helper functions
  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const getConfigStatusColor = (configured: boolean) => {
    return configured ? 'success' : 'error';
  };

  const getSyncStatusSummary = () => {
    const statuses = Object.values(syncStatuses);
    return {
      total: statuses.length,
      completed: statuses.filter((s: any) => s.status === 'completed').length,
      failed: statuses.filter((s: any) => s.status === 'failed').length,
      inProgress: statuses.filter((s: any) => ['started', 'cloning', 'processing'].includes(s.status)).length,
    };
  };

  const syncSummary = getSyncStatusSummary();

  return (
    <>
      <Helmet>
        <title>Dashboard - FactFiber Documentation</title>
        <meta name="description" content="FactFiber documentation system dashboard" />
      </Helmet>

      <Box>
        {/* Welcome Section */}
        <Box sx={{ mb: 4 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            {getGreeting()}, {user?.name || user?.username || 'User'}!
          </Typography>
          <Typography variant="subtitle1" color="text.secondary">
            Welcome to your documentation dashboard. Here's an overview of your system.
          </Typography>
        </Box>

        {/* Stats Cards */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Total Repositories
                    </Typography>
                    <Typography variant="h4">
                      {dashboardLoading ? <Skeleton width={40} /> : dashboard?.total_repositories || 0}
                    </Typography>
                  </Box>
                  <LibraryBooksIcon color="primary" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Accessible Docs
                    </Typography>
                    <Typography variant="h4">
                      {dashboardLoading ? <Skeleton width={40} /> : dashboard?.accessible_repositories || 0}
                    </Typography>
                  </Box>
                  <CheckCircleIcon color="success" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Active Syncs
                    </Typography>
                    <Typography variant="h4">
                      {syncLoading ? <Skeleton width={40} /> : syncSummary.inProgress}
                    </Typography>
                  </Box>
                  <SyncIcon color="info" sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={3}>
            <Card>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="text.secondary" gutterBottom variant="body2">
                      Failed Syncs
                    </Typography>
                    <Typography variant="h4" color={syncSummary.failed > 0 ? 'error.main' : 'text.primary'}>
                      {syncLoading ? <Skeleton width={40} /> : syncSummary.failed}
                    </Typography>
                  </Box>
                  <ErrorIcon color={syncSummary.failed > 0 ? 'error' : 'disabled'} sx={{ fontSize: 40 }} />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        <Grid container spacing={3}>
          {/* System Configuration */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: '100%' }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SettingsIcon />
                System Configuration
              </Typography>
              
              {configLoading ? (
                <Box>
                  {Array.from({ length: 4 }).map((_, i) => (
                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      <Skeleton variant="circular" width={24} height={24} />
                      <Skeleton width="60%" height={20} />
                      <Skeleton width={80} height={24} />
                    </Box>
                  ))}
                </Box>
              ) : (
                <List>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color={getConfigStatusColor(configStatus?.github_configured || false)} />
                    </ListItemIcon>
                    <ListItemText primary="GitHub Integration" />
                    <Chip
                      label={configStatus?.github_configured ? 'Configured' : 'Not Configured'}
                      color={getConfigStatusColor(configStatus?.github_configured || false)}
                      size="small"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color={getConfigStatusColor(configStatus?.oauth2_proxy_configured || false)} />
                    </ListItemIcon>
                    <ListItemText primary="OAuth2-Proxy" />
                    <Chip
                      label={configStatus?.oauth2_proxy_configured ? 'Configured' : 'Not Configured'}
                      color={getConfigStatusColor(configStatus?.oauth2_proxy_configured || false)}
                      size="small"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color={getConfigStatusColor(configStatus?.mkdocs_configured || false)} />
                    </ListItemIcon>
                    <ListItemText primary="MkDocs Configuration" />
                    <Chip
                      label={configStatus?.mkdocs_configured ? 'Configured' : 'Not Configured'}
                      color={getConfigStatusColor(configStatus?.mkdocs_configured || false)}
                      size="small"
                    />
                  </ListItem>
                  <ListItem>
                    <ListItemIcon>
                      <CheckCircleIcon color={getConfigStatusColor(configStatus?.temp_dir_writable || false)} />
                    </ListItemIcon>
                    <ListItemText primary="Temporary Directory" />
                    <Chip
                      label={configStatus?.temp_dir_writable ? 'Writable' : 'Not Writable'}
                      color={getConfigStatusColor(configStatus?.temp_dir_writable || false)}
                      size="small"
                    />
                  </ListItem>
                </List>
              )}
              
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/settings')}
                  fullWidth
                >
                  Configure System
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Recent Activity */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3, height: '100%' }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <ScheduleIcon />
                Recent Activity
              </Typography>
              
              {dashboardLoading ? (
                <Box>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      <Skeleton variant="circular" width={24} height={24} />
                      <Box sx={{ flex: 1 }}>
                        <Skeleton width="80%" height={16} />
                        <Skeleton width="60%" height={14} />
                      </Box>
                    </Box>
                  ))}
                </Box>
              ) : dashboard?.recent_updates && dashboard.recent_updates.length > 0 ? (
                <List>
                  {dashboard.recent_updates.slice(0, 5).map((update, index) => (
                    <ListItem key={index}>
                      <ListItemIcon>
                        <SyncIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={update.message}
                        secondary={new Date(update.updated_at).toLocaleString()}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : (
                <Alert severity="info">
                  No recent activity to display. Start by enrolling some repositories!
                </Alert>
              )}
              
              <Box sx={{ mt: 2 }}>
                <Button
                  variant="outlined"
                  onClick={() => navigate('/repositories')}
                  fullWidth
                >
                  Manage Repositories
                </Button>
              </Box>
            </Paper>
          </Grid>

          {/* Sync Status Overview */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <TrendingUpIcon />
                Sync Status Overview
              </Typography>
              
              {syncLoading ? (
                <Box>
                  <Skeleton width="100%" height={20} sx={{ mb: 2 }} />
                  <Skeleton width="100%" height={10} sx={{ mb: 1 }} />
                  <Skeleton width="80%" height={16} />
                </Box>
              ) : syncSummary.total > 0 ? (
                <Box>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="body2">
                      {syncSummary.completed} of {syncSummary.total} repositories synced
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {Math.round((syncSummary.completed / syncSummary.total) * 100)}%
                    </Typography>
                  </Box>
                  <LinearProgress
                    variant="determinate"
                    value={(syncSummary.completed / syncSummary.total) * 100}
                    sx={{ mb: 2 }}
                  />
                  <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
                    <Chip
                      label={`${syncSummary.completed} Completed`}
                      color="success"
                      size="small"
                    />
                    {syncSummary.inProgress > 0 && (
                      <Chip
                        label={`${syncSummary.inProgress} In Progress`}
                        color="info"
                        size="small"
                      />
                    )}
                    {syncSummary.failed > 0 && (
                      <Chip
                        label={`${syncSummary.failed} Failed`}
                        color="error"
                        size="small"
                      />
                    )}
                  </Box>
                </Box>
              ) : (
                <Alert severity="info">
                  No sync activities detected. Enroll repositories to start syncing documentation.
                </Alert>
              )}
            </Paper>
          </Grid>

          {/* Quick Actions */}
          <Grid item xs={12} md={6}>
            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" gutterBottom>
                Quick Actions
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Button
                    variant="contained"
                    fullWidth
                    startIcon={<LibraryBooksIcon />}
                    onClick={() => navigate('/repositories')}
                  >
                    Manage Repositories
                  </Button>
                </Grid>
                <Grid item xs={12}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<SearchIcon />}
                    onClick={() => navigate('/search')}
                  >
                    Search Documentation
                  </Button>
                </Grid>
                <Grid item xs={12}>
                  <Button
                    variant="outlined"
                    fullWidth
                    startIcon={<SettingsIcon />}
                    onClick={() => navigate('/settings')}
                  >
                    System Settings
                  </Button>
                </Grid>
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      </Box>
    </>
  );
};

export default Dashboard;