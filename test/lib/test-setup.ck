public class ProduceMonDrum {
  fun MonDrum produce() {
    MonDrum mondrum;
    mondrum.init("localhost", "/monome", 14457, 8000, 64, "/mondrum",
                 "localhost", 14030, 14130, "");
    return mondrum;
  }
}
