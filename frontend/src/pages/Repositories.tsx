import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  Card,
  CardContent,
  CardActions,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Snackbar,
  CircularProgress,
  Tabs,
  Tab,
} from '@mui/material';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
  GitHub as GitHubIcon,
  Check as CheckIcon,
  Error as ErrorIcon,
  Sync as SyncIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, Controller } from 'react-hook-form';
import { Helmet } from 'react-helmet-async';

import { apiService } from '@/services/api';
import {
  Repository,
  EnrolledRepository,
  RepositoryEnrollmentForm,
  SyncStatus,
} from '@/types/api';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => (
  <div
    role="tabpanel"
    hidden={value !== index}
    id={`repository-tabpanel-${index}`}
    aria-labelledby={`repository-tab-${index}`}
    {...other}
  >
    {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
  </div>
);

const Repositories: React.FC = () => {
  const [tabValue, setTabValue] = useState(0);
  const [enrollDialogOpen, setEnrollDialogOpen] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<Repository | null>(null);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({ open: false, message: '', severity: 'info' });

  const queryClient = useQueryClient();

  // Form for repository enrollment
  const { control, handleSubmit, reset, formState: { errors } } = useForm<RepositoryEnrollmentForm>({
    defaultValues: {
      repository: '',
      section: 'Projects',
      auto_sync: true,
    },
  });

  // Queries
  const { data: repositories = [], isLoading: repositoriesLoading, refetch: refetchRepositories } = useQuery({
    queryKey: ['repositories'],
    queryFn: apiService.getRepositories,
  });

  const { data: enrolledRepositories = [], isLoading: enrolledLoading, refetch: refetchEnrolled } = useQuery({
    queryKey: ['enrolled-repositories'],
    queryFn: apiService.getEnrolledRepositories,
  });

  const { data: syncStatuses = {} } = useQuery({
    queryKey: ['sync-statuses'],
    queryFn: () => apiService.getSyncStatus() as Promise<Record<string, SyncStatus>>,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Mutations
  const enrollMutation = useMutation({
    mutationFn: apiService.enrollRepository,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrolled-repositories'] });
      setEnrollDialogOpen(false);
      reset();
      setSnackbar({
        open: true,
        message: 'Repository enrolled successfully!',
        severity: 'success',
      });
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message: error.detail || 'Failed to enroll repository',
        severity: 'error',
      });
    },
  });

  const unenrollMutation = useMutation({
    mutationFn: apiService.unenrollRepository,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['enrolled-repositories'] });
      setSnackbar({
        open: true,
        message: 'Repository unenrolled successfully!',
        severity: 'success',
      });
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message: error.detail || 'Failed to unenroll repository',
        severity: 'error',
      });
    },
  });

  const syncMutation = useMutation({
    mutationFn: ({ repository }: { repository: string }) => 
      apiService.triggerSync(repository),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sync-statuses'] });
      setSnackbar({
        open: true,
        message: 'Sync triggered successfully!',
        severity: 'success',
      });
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message: error.detail || 'Failed to trigger sync',
        severity: 'error',
      });
    },
  });

  // Handlers
  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleOpenEnrollDialog = (repo?: Repository) => {
    if (repo) {
      setSelectedRepo(repo);
      reset({
        repository: repo.name,
        section: 'Projects',
        auto_sync: true,
      });
    } else {
      setSelectedRepo(null);
      reset();
    }
    setEnrollDialogOpen(true);
  };

  const handleCloseEnrollDialog = () => {
    setEnrollDialogOpen(false);
    setSelectedRepo(null);
    reset();
  };

  const handleEnrollSubmit = (data: RepositoryEnrollmentForm) => {
    enrollMutation.mutate(data);
  };

  const handleUnenroll = (repositoryName: string) => {
    if (window.confirm(`Are you sure you want to unenroll ${repositoryName}?`)) {
      unenrollMutation.mutate(repositoryName);
    }
  };

  const handleSync = (repositoryName: string) => {
    syncMutation.mutate({ repository: repositoryName });
  };

  const handleRefresh = () => {
    refetchRepositories();
    refetchEnrolled();
  };

  const getSyncStatusChip = (repoName: string) => {
    const status = syncStatuses[repoName];
    if (!status) return null;

    const statusColors = {
      completed: 'success',
      failed: 'error',
      started: 'info',
      cloning: 'info',
      processing: 'warning',
    } as const;

    return (
      <Chip
        size="small"
        label={status.status}
        color={statusColors[status.status as keyof typeof statusColors] || 'default'}
        icon={status.status === 'completed' ? <CheckIcon /> : status.status === 'failed' ? <ErrorIcon /> : <SyncIcon />}
      />
    );
  };

  const isRepositoryEnrolled = (repoName: string) => {
    return enrolledRepositories.some(repo => repo.name === repoName);
  };

  return (
    <>
      <Helmet>
        <title>Repositories - FactFiber Documentation</title>
        <meta name="description" content="Manage documentation repositories and enrollment" />
      </Helmet>

      <Box>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Repository Management
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={handleRefresh}
              disabled={repositoriesLoading || enrolledLoading}
            >
              Refresh
            </Button>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => handleOpenEnrollDialog()}
            >
              Enroll Repository
            </Button>
          </Box>
        </Box>

        <Paper sx={{ width: '100%' }}>
          <Tabs value={tabValue} onChange={handleTabChange} aria-label="repository tabs">
            <Tab label={`Enrolled (${enrolledRepositories.length})`} />
            <Tab label={`Available (${repositories.length})`} />
          </Tabs>

          {/* Enrolled Repositories Tab */}
          <TabPanel value={tabValue} index={0}>
            {enrolledLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : enrolledRepositories.length === 0 ? (
              <Alert severity="info">
                No repositories enrolled yet. Switch to the "Available" tab to enroll repositories.
              </Alert>
            ) : (
              <Grid container spacing={3}>
                {enrolledRepositories.map((repo) => (
                  <Grid item xs={12} md={6} lg={4} key={repo.name}>
                    <Card>
                      <CardContent>
                        <Typography variant="h6" gutterBottom>
                          {repo.name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          Section: {repo.section}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                          <Chip size="small" label="Enrolled" color="success" />
                          {getSyncStatusChip(repo.name)}
                        </Box>
                        {repo.last_sync && (
                          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                            Last sync: {new Date(repo.last_sync).toLocaleString()}
                          </Typography>
                        )}
                      </CardContent>
                      <CardActions>
                        <Button
                          size="small"
                          startIcon={<SyncIcon />}
                          onClick={() => handleSync(repo.name)}
                          disabled={syncMutation.isPending}
                        >
                          Sync
                        </Button>
                        <Button
                          size="small"
                          color="error"
                          startIcon={<DeleteIcon />}
                          onClick={() => handleUnenroll(repo.name)}
                          disabled={unenrollMutation.isPending}
                        >
                          Unenroll
                        </Button>
                      </CardActions>
                    </Card>
                  </Grid>
                ))}
              </Grid>
            )}
          </TabPanel>

          {/* Available Repositories Tab */}
          <TabPanel value={tabValue} index={1}>
            {repositoriesLoading ? (
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            ) : repositories.length === 0 ? (
              <Alert severity="warning">
                No repositories found. Make sure your GitHub token has access to the organization repositories.
              </Alert>
            ) : (
              <Grid container spacing={3}>
                {repositories.map((repo) => {
                  const enrolled = isRepositoryEnrolled(repo.name);
                  return (
                    <Grid item xs={12} md={6} lg={4} key={repo.name}>
                      <Card>
                        <CardContent>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <GitHubIcon fontSize="small" />
                            <Typography variant="h6">{repo.name}</Typography>
                          </Box>
                          <Typography variant="body2" color="text.secondary" gutterBottom>
                            {repo.description || 'No description available'}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
                            {enrolled ? (
                              <Chip size="small" label="Enrolled" color="success" />
                            ) : (
                              <Chip size="small" label="Not Enrolled" />
                            )}
                            {repo.has_docs && (
                              <Chip size="small" label="Has Docs" color="info" />
                            )}
                            {repo.is_private && (
                              <Chip size="small" label="Private" color="warning" />
                            )}
                            {repo.language && (
                              <Chip size="small" label={repo.language} variant="outlined" />
                            )}
                          </Box>
                          <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                            ⭐ {repo.stars} • 🍴 {repo.forks} • Updated: {new Date(repo.last_updated).toLocaleDateString()}
                          </Typography>
                        </CardContent>
                        <CardActions>
                          <Button
                            size="small"
                            variant={enrolled ? "outlined" : "contained"}
                            onClick={() => enrolled ? handleUnenroll(repo.name) : handleOpenEnrollDialog(repo)}
                            disabled={enrollMutation.isPending || unenrollMutation.isPending}
                          >
                            {enrolled ? 'Unenroll' : 'Enroll'}
                          </Button>
                          <Button
                            size="small"
                            href={repo.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            View on GitHub
                          </Button>
                        </CardActions>
                      </Card>
                    </Grid>
                  );
                })}
              </Grid>
            )}
          </TabPanel>
        </Paper>

        {/* Enrollment Dialog */}
        <Dialog open={enrollDialogOpen} onClose={handleCloseEnrollDialog} maxWidth="sm" fullWidth>
          <form onSubmit={handleSubmit(handleEnrollSubmit)}>
            <DialogTitle>
              {selectedRepo ? `Enroll ${selectedRepo.name}` : 'Enroll Repository'}
            </DialogTitle>
            <DialogContent>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 1 }}>
                <Controller
                  name="repository"
                  control={control}
                  rules={{ required: 'Repository name is required' }}
                  render={({ field }) => (
                    <TextField
                      {...field}
                      label="Repository Name"
                      fullWidth
                      error={!!errors.repository}
                      helperText={errors.repository?.message}
                      disabled={!!selectedRepo}
                      placeholder="org/repository-name"
                    />
                  )}
                />
                <Controller
                  name="section"
                  control={control}
                  rules={{ required: 'Section is required' }}
                  render={({ field }) => (
                    <FormControl fullWidth error={!!errors.section}>
                      <InputLabel>Documentation Section</InputLabel>
                      <Select {...field} label="Documentation Section">
                        <MenuItem value="Projects">Projects</MenuItem>
                        <MenuItem value="AI/ML Tools">AI/ML Tools</MenuItem>
                        <MenuItem value="Infrastructure">Infrastructure</MenuItem>
                        <MenuItem value="Libraries">Libraries</MenuItem>
                        <MenuItem value="Documentation">Documentation</MenuItem>
                        <MenuItem value="Other">Other</MenuItem>
                      </Select>
                    </FormControl>
                  )}
                />
              </Box>
            </DialogContent>
            <DialogActions>
              <Button onClick={handleCloseEnrollDialog}>Cancel</Button>
              <Button
                type="submit"
                variant="contained"
                disabled={enrollMutation.isPending}
                startIcon={enrollMutation.isPending ? <CircularProgress size={20} /> : undefined}
              >
                {enrollMutation.isPending ? 'Enrolling...' : 'Enroll'}
              </Button>
            </DialogActions>
          </form>
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

export default Repositories;