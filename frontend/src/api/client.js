const API_BASE = (import.meta.env.VITE_API_URL || 'http://localhost:8000') + '/api';

async function request(endpoint, options = {}) {
  const { params, method = 'GET', body } = options;

  let url = `${API_BASE}${endpoint}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        searchParams.append(key, value);
      }
    });
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const fetchOptions = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };

  if (body && method !== 'GET') {
    fetchOptions.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(url, fetchOptions);
    if (!response.ok) {
      const errorBody = await response.text();
      throw new Error(`API Error ${response.status}: ${errorBody}`);
    }
    if (response.status === 204) return null;
    return await response.json();
  } catch (error) {
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      throw new Error('Network error: Unable to reach the API server.');
    }
    throw error;
  }
}

export async function fetchArticles(params = {}) {
  return request('/articles', { params });
}

export async function fetchGraphData(params = {}) {
  return request('/graph', { params });
}

export async function fetchTopics() {
  return request('/topics');
}

export async function createTopic(data) {
  return request('/topics', { method: 'POST', body: data });
}

export async function updateTopic(id, data) {
  return request(`/topics/${id}`, { method: 'PUT', body: data });
}

export async function deleteTopic(id) {
  return request(`/topics/${id}`, { method: 'DELETE' });
}

export async function scrapeTopic(topicId) {
  return request(`/topics/${topicId}/scrape`, { method: 'POST' });
}

export async function fetchOilPrice() {
  return request('/oil-price');
}
