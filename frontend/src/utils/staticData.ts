import { ServerWithExtras, ServersData } from '../types/server';

export class StaticDataManager {
  private serversData: ServersData = { servers: [], total: 0 };

  setServers(data: ServersData) {
    this.serversData = data;
  }

  getServers(): ServerWithExtras[] {
    return this.serversData.servers;
  }

  getTotalServers(): number {
    return this.serversData.total;
  }
}

export const staticData = new StaticDataManager(); 