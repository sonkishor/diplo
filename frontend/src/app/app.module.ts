import { NgModule } from "@angular/core";
import { BrowserModule } from "@angular/platform-browser";
import { HttpClientModule } from "@angular/common/http";
import { AppRoutingModule } from "./app-routing.module";
import { AppComponent } from "./app.component";
import { MapComponent } from "./map/map.component";
import { CommonModule, DecimalPipe } from "@angular/common";
import { FormsModule } from "@angular/forms";

@NgModule({
  providers: [DecimalPipe],
  declarations: [AppComponent, MapComponent],
  imports: [BrowserModule, AppRoutingModule, HttpClientModule, FormsModule],
  bootstrap: [AppComponent],
})
export class AppModule {}
