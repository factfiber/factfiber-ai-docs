import React, { useState, useEffect } from 'react';
import {
  Box,
  TextField,
  Button,
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Checkbox,
  ListItemIcon,
  Alert,
  CircularProgress,
  Pagination,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Grid,
  Skeleton,
} from '@mui/material';
import {
  Search as SearchIcon,
  Clear as ClearIcon,
  FilterList as FilterIcon,
  ExpandMore as ExpandMoreIcon,
  Description as DescriptionIcon,
  Code as CodeIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

import { apiService } from '@/services/api';
import { SearchQuery, SearchResult, SearchResponse } from '@/types/api';

const ITEMS_PER_PAGE = 10;

const Search: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState(searchParams.get('q') || '');
  const [selectedRepositories, setSelectedRepositories] = useState<string[]>([]);
  const [selectedSections, setSelectedSections] = useState<string[]>([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [searchTriggered, setSearchTriggered] = useState(false);

  // Get available repositories for filtering
  const { data: enrolledRepositories = [] } = useQuery({
    queryKey: ['enrolled-repositories'],
    queryFn: apiService.getEnrolledRepositories,
  });

  // Available sections for filtering
  const availableSections = [
    'Guide',
    'API',
    'Source',
    'Reference',
    'Tutorial',
    'Examples',
    'Configuration',
  ];

  // Search query
  const searchQuery: SearchQuery = {
    query,
    repositories: selectedRepositories,
    sections: selectedSections,
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
  };

  const {
    data: searchResults,
    isLoading: searchLoading,
    error: searchError,
  } = useQuery({
    queryKey: ['search', searchQuery],
    queryFn: () => apiService.search(searchQuery),
    enabled: searchTriggered && query.trim().length > 0,
  });

  // Update URL when search parameters change
  useEffect(() => {
    if (query) {
      setSearchParams({ q: query });
    } else {
      setSearchParams({});
    }
  }, [query, setSearchParams]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setCurrentPage(1);
      setSearchTriggered(true);
    }
  };

  const handleClearSearch = () => {
    setQuery('');
    setSelectedRepositories([]);
    setSelectedSections([]);
    setCurrentPage(1);
    setSearchTriggered(false);
  };

  const handleRepositoryChange = (event: any) => {
    setSelectedRepositories(event.target.value);
    setCurrentPage(1);
  };

  const handleSectionChange = (event: any) => {
    setSelectedSections(event.target.value);
    setCurrentPage(1);
  };

  const handlePageChange = (event: React.ChangeEvent<unknown>, page: number) => {
    setCurrentPage(page);
  };

  const getResultIcon = (result: SearchResult) => {
    if (result.metadata?.type === 'api') {
      return <CodeIcon color="primary" />;
    }
    return <DescriptionIcon color="action" />;
  };

  const formatExecutionTime = (timeMs: number) => {
    if (timeMs < 1000) {
      return `${Math.round(timeMs)}ms`;
    }
    return `${(timeMs / 1000).toFixed(2)}s`;
  };

  const highlightSearchTerm = (text: string, searchTerm: string) => {
    if (!searchTerm.trim()) return text;
    
    const regex = new RegExp(`(${searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);
    
    return parts.map((part, index) =>
      regex.test(part) ? (
        <mark key={index} style={{ backgroundColor: '#ffeb3b', padding: '0 2px' }}>
          {part}
        </mark>
      ) : (
        part
      )
    );
  };

  const totalPages = searchResults ? Math.ceil(searchResults.total_results / ITEMS_PER_PAGE) : 0;

  return (
    <>
      <Helmet>
        <title>{query ? `Search: ${query}` : 'Search'} - FactFiber Documentation</title>
        <meta name="description" content="Search across all FactFiber documentation repositories" />
      </Helmet>

      <Box>
        <Typography variant="h4" component="h1" gutterBottom>
          Search Documentation
        </Typography>

        {/* Search Form */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <form onSubmit={handleSearch}>
            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={6}>
                <TextField
                  fullWidth
                  label="Search query"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Enter your search terms..."
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                    endAdornment: query && (
                      <InputAdornment position="end">
                        <Button
                          size="small"
                          onClick={() => setQuery('')}
                          startIcon={<ClearIcon />}
                        >
                          Clear
                        </Button>
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
              <Grid item xs={12} md={3}>
                <Button
                  type="submit"
                  variant="contained"
                  fullWidth
                  disabled={!query.trim() || searchLoading}
                  startIcon={searchLoading ? <CircularProgress size={20} /> : <SearchIcon />}
                >
                  {searchLoading ? 'Searching...' : 'Search'}
                </Button>
              </Grid>
              <Grid item xs={12} md={3}>
                <Button
                  variant="outlined"
                  fullWidth
                  onClick={handleClearSearch}
                  startIcon={<ClearIcon />}
                >
                  Clear All
                </Button>
              </Grid>
            </Grid>
          </form>
        </Paper>

        {/* Filters */}
        <Accordion sx={{ mb: 3 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FilterIcon />
              <Typography>Search Filters</Typography>
              {(selectedRepositories.length > 0 || selectedSections.length > 0) && (
                <Chip
                  label={`${selectedRepositories.length + selectedSections.length} active`}
                  size="small"
                  color="primary"
                />
              )}
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Filter by Repository</InputLabel>
                  <Select
                    multiple
                    value={selectedRepositories}
                    onChange={handleRepositoryChange}
                    input={<OutlinedInput label="Filter by Repository" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {enrolledRepositories.map((repo) => (
                      <MenuItem key={repo.name} value={repo.name}>
                        <Checkbox checked={selectedRepositories.indexOf(repo.name) > -1} />
                        <ListItemText primary={repo.name} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} md={6}>
                <FormControl fullWidth>
                  <InputLabel>Filter by Section</InputLabel>
                  <Select
                    multiple
                    value={selectedSections}
                    onChange={handleSectionChange}
                    input={<OutlinedInput label="Filter by Section" />}
                    renderValue={(selected) => (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {selected.map((value) => (
                          <Chip key={value} label={value} size="small" />
                        ))}
                      </Box>
                    )}
                  >
                    {availableSections.map((section) => (
                      <MenuItem key={section} value={section}>
                        <Checkbox checked={selectedSections.indexOf(section) > -1} />
                        <ListItemText primary={section} />
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
            </Grid>
          </AccordionDetails>
        </Accordion>

        {/* Search Results */}
        {searchError && (
          <Alert severity="error" sx={{ mb: 3 }}>
            Search failed: {(searchError as any).detail || 'An error occurred while searching'}
          </Alert>
        )}

        {searchLoading && (
          <Box>
            {Array.from({ length: 5 }).map((_, index) => (
              <Paper key={index} sx={{ p: 2, mb: 2 }}>
                <Skeleton variant="text" width="60%" height={24} />
                <Skeleton variant="text" width="100%" height={16} />
                <Skeleton variant="text" width="80%" height={16} />
                <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                  <Skeleton variant="rounded" width={60} height={20} />
                  <Skeleton variant="rounded" width={80} height={20} />
                </Box>
              </Paper>
            ))}
          </Box>
        )}

        {searchResults && !searchLoading && (
          <>
            {/* Search Stats */}
            <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                {searchResults.filtered_results} results found
                {searchResults.repositories_searched.length > 0 && (
                  <> in {searchResults.repositories_searched.length} repositories</>
                )}
                <Typography component="span" sx={{ ml: 1 }}>
                  ({formatExecutionTime(searchResults.execution_time_ms)})
                </Typography>
              </Typography>
              {searchResults.repositories_searched.length > 0 && (
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {searchResults.repositories_searched.slice(0, 3).map((repo) => (
                    <Chip key={repo} label={repo} size="small" variant="outlined" />
                  ))}
                  {searchResults.repositories_searched.length > 3 && (
                    <Chip
                      label={`+${searchResults.repositories_searched.length - 3} more`}
                      size="small"
                      variant="outlined"
                    />
                  )}
                </Box>
              )}
            </Box>

            {/* Results List */}
            {searchResults.results.length === 0 ? (
              <Alert severity="info">
                No results found for "{query}". Try adjusting your search terms or filters.
              </Alert>
            ) : (
              <>
                <List>
                  {searchResults.results.map((result, index) => (
                    <ListItem
                      key={`${result.repository}-${result.url}-${index}`}
                      component={Paper}
                      sx={{ mb: 2, flexDirection: 'column', alignItems: 'stretch' }}
                    >
                      <Box sx={{ display: 'flex', width: '100%', p: 1 }}>
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          {getResultIcon(result)}
                        </ListItemIcon>
                        <Box sx={{ flex: 1 }}>
                          <Typography
                            variant="h6"
                            component="a"
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            sx={{
                              textDecoration: 'none',
                              color: 'primary.main',
                              '&:hover': {
                                textDecoration: 'underline',
                              },
                            }}
                          >
                            {highlightSearchTerm(result.title, query)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" paragraph>
                            {highlightSearchTerm(result.content.substring(0, 300), query)}
                            {result.content.length > 300 && '...'}
                          </Typography>
                          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                            <Chip
                              label={result.repository}
                              size="small"
                              color="primary"
                              variant="outlined"
                            />
                            {result.section && (
                              <Chip
                                label={result.section}
                                size="small"
                                variant="outlined"
                              />
                            )}
                            <Chip
                              label={`${Math.round(result.score * 100)}% match`}
                              size="small"
                              color="success"
                              variant="outlined"
                            />
                            {result.metadata?.type && (
                              <Chip
                                label={result.metadata.type}
                                size="small"
                                variant="outlined"
                              />
                            )}
                          </Box>
                        </Box>
                      </Box>
                    </ListItem>
                  ))}
                </List>

                {/* Pagination */}
                {totalPages > 1 && (
                  <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                    <Pagination
                      count={totalPages}
                      page={currentPage}
                      onChange={handlePageChange}
                      color="primary"
                      size="large"
                    />
                  </Box>
                )}
              </>
            )}
          </>
        )}

        {!searchTriggered && !searchLoading && (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <SearchIcon sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Search across all documentation
            </Typography>
            <Typography variant="body1" color="text.secondary">
              Enter your search terms above to find relevant documentation across all enrolled repositories.
              Use filters to narrow down your search by repository or section.
            </Typography>
          </Paper>
        )}
      </Box>
    </>
  );
};

export default Search;