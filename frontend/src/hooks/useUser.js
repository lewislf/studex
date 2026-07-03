export function useUser(json) {
    return {
        id: json.id || '',
        name: json.profile?.display_name || 'Usuário',
        email: json.profile?.email || '',
        avatar: json.profile?.photo || '',
        metrics: {
            streak: Number(json.gamification?.current_streak) || 0,
            summariesCount: Number(json.counters?.summaries) || 0,
            mapsCount: Number(json.counters?.mind_maps) || 0,
            queueCount: Number(json.counters?.pending_items) || 0,
        },
        collections: (json.items || []).map(item => ({
            id: item.id,
            title: item.title || 'Sem título',
            subtitle: item.subtitle || '',
            value: Number(item.metric) || 0,
            color: item.tag_color || '#gray'
        }))
    };
}
