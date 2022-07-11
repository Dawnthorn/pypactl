class SinkInfo:
    def __init__(self):
        self.index = None,
        self.name = None,
        self.description = None,
        self.sample_spec = None,
        self.channel_map = None,
        self.owner_module = None,
        self.mute = None
        self.monitor_source = None
        self.monitor_source_name = None
        self.latency = None
        self.driver = None
        self.flags = None
        self.proplist = {}
        self.configured_latency = None
        self.base_volume = None
        self.state = None
        self.n_volume_steps = None
        self.n_ports = None
        self.ports = None
        self.ap = None
        self.formats = None
        self.active_port = None


    def __repr__(self):
        return f"<SinkInfo index={self.index} name={self.name} description={self.description} sample_spec={self.sample_spec} channel_map={self.channel_map} owner_module={self.owner_module} mute={self.mute} monitor_source={self.monitor_source} monitor_source_name={self.monitor_source_name} latency={self.latency} driver={self.driver} flags={self.flags} proplist={self.proplist} configured_latency={self.configured_latency} base_volume={self.base_volume} state={self.state} n_volume_steps={self.n_volume_steps} n_ports={self.n_ports} ports={self.ports} ap={self.ap} formats={self.formats}>"
